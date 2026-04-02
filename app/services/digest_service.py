"""
Digest Service: gera e persiste um digest estruturado do schema do banco vinculado ao agente.

Responsabilidades:
- Ler schema real do banco via db_introspection
- Gerar DigestData estruturado (sem LLM)
- Salvar em data/digests/{agent_id}.digest.json
- Salvar versão Markdown resumida em data/digests/{agent_id}.digest.md
- Permitir regeneração sob demanda

IMPORTANTE: não substitui introspecção real para ações críticas.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.core.logger import get_logger
from app.core.settings import settings
from app.schemas.agent import AgentConfig
from app.schemas.digest import (
    ColumnInfo,
    DBDigest,
    DigestStatus,
    DigestSummary,
    ForeignKeyInfo,
    RelationshipInfo,
    RoutineDigest,
    TableDigest,
    TriggerDigest,
)
from app.tools import db_introspection

logger = get_logger("digest_service")


# ─── Caminhos ─────────────────────────────────────────────────────────────────

def _json_path(agent_id: str) -> Path:
    return settings.digests_path / f"{agent_id}.digest.json"


def _md_path(agent_id: str) -> Path:
    return settings.digests_path / f"{agent_id}.digest.md"


# ─── API Pública ──────────────────────────────────────────────────────────────

def generate_digest(agent: AgentConfig) -> DBDigest:
    """
    Gera digest completo do banco vinculado ao agente e persiste em disco.
    Não usa LLM — usa apenas introspecção real.
    """
    logger.info(f"[DIGEST] Gerando digest para agente={agent.id}, banco={agent.database.name if agent.database else '?'}")

    if not agent.database:
        raise ValueError(f"Agente '{agent.id}' não possui banco de dados configurado")

    tables = _collect_tables(agent)
    views = _collect_views(agent)
    triggers = _collect_triggers(agent)
    procedures = _collect_routines(agent, "list_procedures")
    functions = _collect_routines(agent, "list_functions")

    # Coletar relacionamentos reais a partir das FKs de todas as tabelas
    table_names = {t.name for t in tables}
    relationships = _build_relationships(tables, table_names)

    summary = DigestSummary(
        tables=len(tables),
        views=len(views),
        triggers=len(triggers),
        procedures=len(procedures),
        functions=len(functions),
        relationships=len(relationships),
    )

    digest = DBDigest(
        agent_id=agent.id,
        database=agent.database.name,
        generated_at=datetime.now(timezone.utc),
        summary=summary,
        tables=tables,
        views=views,
        triggers=triggers,
        procedures=procedures,
        functions=functions,
        relationships=relationships,
    )

    _persist_json(digest)
    _persist_md(digest)

    logger.info(
        f"[DIGEST] Concluído | tabelas={summary.tables} | views={summary.views} "
        f"| triggers={summary.triggers} | procs={summary.procedures} | funcs={summary.functions} "
        f"| relacionamentos={summary.relationships}"
    )
    return digest


def load_digest(agent_id: str) -> Optional[DBDigest]:
    """Carrega digest salvo em disco. Retorna None se não existir."""
    path = _json_path(agent_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return DBDigest.model_validate(data)
    except Exception as e:
        logger.error(f"[DIGEST] Erro ao carregar digest '{agent_id}': {e}")
        return None


def get_digest_status(agent_id: str) -> DigestStatus:
    """Retorna status (existe? quando? quantas tabelas?)"""
    digest = load_digest(agent_id)
    if not digest:
        return DigestStatus(agent_id=agent_id, exists=False)
    return DigestStatus(
        agent_id=agent_id,
        exists=True,
        generated_at=digest.generated_at,
        tables=digest.summary.tables,
        views=digest.summary.views,
        triggers=digest.summary.triggers,
        procedures=digest.summary.procedures,
        functions=digest.summary.functions,
    )


# ─── Coleta de Schema ─────────────────────────────────────────────────────────

def _collect_tables(agent: AgentConfig) -> list[TableDigest]:
    result = db_introspection.list_tables(agent)
    if not result.success or not result.rows:
        logger.warning(f"[DIGEST] Sem tabelas encontradas: {result.error}")
        return []

    table_names = [list(row.values())[0] for row in result.rows if row]
    digests = []
    for name in table_names:
        td = _build_table_digest(agent, name, "BASE TABLE")
        if td:
            digests.append(td)
    return digests


def _collect_views(agent: AgentConfig) -> list[TableDigest]:
    result = db_introspection.list_views(agent)
    if not result.success or not result.rows:
        return []

    view_names = [list(row.values())[0] for row in result.rows if row]
    digests = []
    for name in view_names:
        td = _build_table_digest(agent, name, "VIEW")
        if td:
            digests.append(td)
    return digests


def _collect_triggers(agent: AgentConfig) -> list[TriggerDigest]:
    result = db_introspection.list_triggers(agent)
    if not result.success or not result.rows:
        return []

    triggers = []
    for row in result.rows:
        triggers.append(TriggerDigest(
            name=row.get("Trigger", row.get("TRIGGER_NAME", "")),
            event=row.get("Event", row.get("EVENT_MANIPULATION", "")),
            timing=row.get("Timing", row.get("ACTION_TIMING", "")),
            table=row.get("Table", row.get("EVENT_OBJECT_TABLE", "")),
        ))
    return triggers


def _collect_routines(agent: AgentConfig, action: str) -> list[RoutineDigest]:
    result = db_introspection.introspect(agent, action)
    if not result.success or not result.rows:
        return []

    routines = []
    for row in result.rows:
        name = row.get("Name", row.get("ROUTINE_NAME", ""))
        rtype = row.get("Type", row.get("ROUTINE_TYPE", action.replace("list_", "").upper()))
        if name:
            routines.append(RoutineDigest(name=name, type=rtype))
    return routines


def _build_table_digest(agent: AgentConfig, name: str, table_type: str) -> Optional[TableDigest]:
    """Constrói TableDigest com colunas, PKs e FKs para uma tabela/view."""
    try:
        columns = _get_columns(agent, name)
        pk = _extract_pk(columns)
        fks = _get_foreign_keys(agent, name) if table_type == "BASE TABLE" else []
        related = list({fk.ref_table for fk in fks})
        description = _heuristic_description(name, columns, fks)

        return TableDigest(
            name=name,
            type=table_type,
            primary_key=pk,
            columns=columns,
            foreign_keys=fks,
            related_tables=related,
            description=description,
        )
    except Exception as e:
        logger.warning(f"[DIGEST] Erro ao processar tabela '{name}': {e}")
        return TableDigest(name=name, type=table_type, description="(erro na coleta)")


def _get_columns(agent: AgentConfig, table_name: str) -> list[ColumnInfo]:
    result = db_introspection.get_columns(agent, table_name)
    if not result.success or not result.rows:
        # Fallback: DESCRIBE
        desc = db_introspection.describe_table(agent, table_name)
        if not desc.success or not desc.rows:
            return []
        return [
            ColumnInfo(
                name=row.get("Field", ""),
                type=row.get("Type", ""),
                nullable=row.get("Null", "YES") == "YES",
                default=row.get("Default"),
                extra=_build_col_extra(row.get("Extra", ""), row.get("Key", "")),
            )
            for row in desc.rows if row.get("Field")
        ]

    return [
        ColumnInfo(
            name=row.get("COLUMN_NAME", ""),
            type=row.get("COLUMN_TYPE", row.get("DATA_TYPE", "")),
            nullable=row.get("IS_NULLABLE", "YES") == "YES",
            default=str(row["COLUMN_DEFAULT"]) if row.get("COLUMN_DEFAULT") is not None else None,
            comment=row.get("COLUMN_COMMENT") or None,
            extra=_build_col_extra(row.get("EXTRA", ""), row.get("COLUMN_KEY", "")),
        )
        for row in result.rows if row.get("COLUMN_NAME")
    ]


def _get_foreign_keys(agent: AgentConfig, table_name: str) -> list[ForeignKeyInfo]:
    result = db_introspection.get_foreign_keys(agent, table_name)
    if not result.success or not result.rows:
        return []
    return [
        ForeignKeyInfo(
            constraint_name=row.get("CONSTRAINT_NAME", ""),
            column=row.get("COLUMN_NAME", ""),
            ref_table=row.get("REFERENCED_TABLE_NAME", ""),
            ref_column=row.get("REFERENCED_COLUMN_NAME", ""),
        )
        for row in result.rows if row.get("REFERENCED_TABLE_NAME")
    ]


def _build_relationships(tables: list[TableDigest], table_names: set[str]) -> list[RelationshipInfo]:
    """
    Constrói a lista de relacionamentos reais do banco a partir das FKs de cada tabela.

    Regras:
    - apenas FKs explícitas — nunca inventa relação
    - a tabela referenciada deve existir no digest (tabela real)
    - deduplicação por (source_table, source_column, target_table, target_column)
    """
    seen: set[tuple[str, str, str, str]] = set()
    relationships: list[RelationshipInfo] = []

    for table in tables:
        for fk in table.foreign_keys:
            if fk.ref_table not in table_names:
                # Referência externa ao digest — ignorar (a tabela destino não foi coletada)
                logger.debug(
                    f"[DIGEST] FK ignorada (ref fora do digest): "
                    f"{table.name}.{fk.column} → {fk.ref_table}.{fk.ref_column}"
                )
                continue

            key = (table.name, fk.column, fk.ref_table, fk.ref_column)
            if key in seen:
                continue
            seen.add(key)

            relationships.append(
                RelationshipInfo(
                    source_table=table.name,
                    source_column=fk.column,
                    target_table=fk.ref_table,
                    target_column=fk.ref_column,
                    constraint_name=fk.constraint_name,
                    relationship_type="many-to-one",
                )
            )

    logger.info(f"[DIGEST] Relacionamentos detectados: {len(relationships)}")
    return relationships


def _build_col_extra(mysql_extra: str, column_key: str) -> Optional[str]:
    """Combina EXTRA e COLUMN_KEY em um campo legível para _extract_pk."""
    parts = [p for p in [mysql_extra or "", "PRI" if (column_key or "").upper() == "PRI" else ""] if p]
    return " ".join(parts) or None


def _extract_pk(columns: list[ColumnInfo]) -> Optional[str]:
    # Prioridade 1: coluna marcada PRI via COLUMN_KEY (INFORMATION_SCHEMA) ou Key=PRI (DESCRIBE)
    for col in columns:
        if col.extra and "PRI" in col.extra.upper():
            return col.name
    # Prioridade 2: coluna auto_increment (heurística MySQL)
    for col in columns:
        if col.extra and "auto_increment" in col.extra.lower():
            return col.name
    return None


# ─── Heurística de Descrição ──────────────────────────────────────────────────

def _heuristic_description(name: str, columns: list[ColumnInfo], fks: list[ForeignKeyInfo]) -> str:
    """Gera descrição curta sem LLM baseada em heurísticas."""
    col_names = [c.name.lower() for c in columns]
    n = name.lower()

    parts: list[str] = []

    # Detectar padrões comuns pelo nome da tabela
    if any(k in n for k in ("log", "audit", "historico", "history")):
        parts.append("Tabela de log/auditoria")
    elif any(k in n for k in ("config", "setting", "parametro", "param")):
        parts.append("Tabela de configurações/parâmetros")
    elif any(k in n for k in ("user", "usuario", "pessoa", "person", "member", "membro")):
        parts.append("Entidade de usuário/pessoa")
    elif any(k in n for k in ("product", "produto", "item", "catalog", "catalogo")):
        parts.append("Catálogo/produto")
    elif any(k in n for k in ("order", "pedido", "venda", "sale")):
        parts.append("Pedido/transação comercial")
    elif any(k in n for k in ("category", "categoria", "tag", "tipo", "type")):
        parts.append("Categoria/classificação")
    elif any(k in n for k in ("address", "endereco", "location", "localizacao")):
        parts.append("Endereço/localização")

    # Resumo de colunas
    if columns:
        parts.append(f"{len(columns)} coluna(s)")

    # Relacionamentos
    if fks:
        refs = list({fk.ref_table for fk in fks})
        parts.append(f"Relacionada a: {', '.join(refs[:3])}")

    return ". ".join(parts) if parts else f"Tabela {name}"


# ─── Persistência ─────────────────────────────────────────────────────────────

def _persist_json(digest: DBDigest) -> None:
    path = _json_path(digest.agent_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(
            digest.model_dump_json(indent=2),
            encoding="utf-8",
        )
        logger.debug(f"[DIGEST] JSON salvo: {path}")
    except Exception as e:
        logger.error(f"[DIGEST] Erro ao salvar JSON: {e}")
        raise


def _persist_md(digest: DBDigest) -> None:
    path = _md_path(digest.agent_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(_render_md(digest), encoding="utf-8")
        logger.debug(f"[DIGEST] MD salvo: {path}")
    except Exception as e:
        logger.error(f"[DIGEST] Erro ao salvar MD: {e}")
        raise


def _render_md(digest: DBDigest) -> str:
    lines: list[str] = [
        f"# DB Digest — {digest.database}",
        f"**Agente:** `{digest.agent_id}`  ",
        f"**Banco:** `{digest.database}`  ",
        f"**Gerado em:** {digest.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
        "",
        "## Resumo",
        f"| Objeto | Qtd |",
        f"|--------|-----|",
        f"| Tabelas | {digest.summary.tables} |",
        f"| Views | {digest.summary.views} |",
        f"| Triggers | {digest.summary.triggers} |",
        f"| Procedures | {digest.summary.procedures} |",
        f"| Functions | {digest.summary.functions} |",
        "",
    ]

    if digest.tables:
        lines.append("## Tabelas")
        for t in digest.tables:
            lines.append(f"\n### `{t.name}`")
            if t.description:
                lines.append(f"_{t.description}_")
            if t.primary_key:
                lines.append(f"**PK:** `{t.primary_key}`")
            if t.columns:
                lines.append("")
                lines.append("| Coluna | Tipo | Nullable |")
                lines.append("|--------|------|----------|")
                for col in t.columns:
                    nullable = "Sim" if col.nullable else "Não"
                    lines.append(f"| `{col.name}` | `{col.type}` | {nullable} |")
            if t.foreign_keys:
                lines.append("")
                lines.append("**FKs:**")
                for fk in t.foreign_keys:
                    lines.append(f"- `{fk.column}` → `{fk.ref_table}.{fk.ref_column}`")

    if digest.relationships:
        lines.append("\n## Relacionamentos")
        lines.append("| Origem | Coluna FK | Destino | Coluna ref. | Constraint |")
        lines.append("|--------|-----------|---------|-------------|------------|")
        for rel in digest.relationships:
            lines.append(
                f"| `{rel.source_table}` | `{rel.source_column}` | `{rel.target_table}` | `{rel.target_column}` | `{rel.constraint_name}` |"
            )

    if digest.views:
        lines.append("\n## Views")
        for v in digest.views:
            lines.append(f"- `{v.name}`" + (f" — {v.description}" if v.description else ""))

    if digest.triggers:
        lines.append("\n## Triggers")
        for tr in digest.triggers:
            lines.append(f"- `{tr.name}` ({tr.timing} {tr.event} ON `{tr.table}`)")

    if digest.procedures:
        lines.append("\n## Procedures")
        for p in digest.procedures:
            lines.append(f"- `{p.name}`")

    if digest.functions:
        lines.append("\n## Functions")
        for f in digest.functions:
            lines.append(f"- `{f.name}`")

    return "\n".join(lines)
