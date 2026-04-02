"""
Query Builder: constrói SQL seguro a partir de um plano estruturado.

Responsabilidades:
- Validar table/column names contra o digest (whitelist)
- Gerar SQL parametrizado com backtick-escaping
- Suportar planos SELECT, COUNT, SELECT com JOIN simples
- Retornar None (com motivo) para planos de baixa confiança ou inválidos

Design de segurança:
- NUNCA interpola valores de usuário diretamente no SQL
- Usa placeholders %s e retorna dict de parâmetros posicionais
- Todo nome de tabela e coluna é verificado contra o digest antes de usar
- Apenas operações de leitura (SELECT/COUNT) são geradas
- LIMIT máximo fixo em 1000 para evitar dump acidental de toda a tabela

"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional, Union, List

from app.schemas.digest import DBDigest
from app.services.filter_parser import QueryFilter, OrderByClause
from app.services.join_resolver import JoinPath, get_table_from_digest

logger = logging.getLogger(__name__)

# Limite máximo absoluto — nunca retorna mais que isso mesmo que o usuário peça
_HARD_MAX_LIMIT = 1000
_DEFAULT_LIMIT = 50

# Confiança mínima para emitir SQL
_MIN_CONFIDENCE = 0.70


# ─── Plano de consulta ────────────────────────────────────────────────────────

@dataclass
class V2Plan:
    """
    Plano de consulta construído pelo fastpath_v2_service antes de chamar o builder.

    Campos:
        intent    : "SELECT" | "COUNT" | "SELECT_JOIN" | "COUNT_JOIN"
        tables    : lista de nomes de tabela (1 para simples, 2 para join)
        filters   : filtros extraídos pelo filter_parser
        order_by  : cláusulas de ordenação
        limit     : limite de linhas (None → usa _DEFAULT_LIMIT)
        join_path : JoinPath se intent contém JOIN
        confidence: 0.0-1.0 — abaixo de _MIN_CONFIDENCE o builder recusa
    """
    intent: str
    tables: list[str]
    columns: list[str] = field(default_factory=list) # Novo: suporte a SELECT col1, col2
    filters: list[QueryFilter] = field(default_factory=list)
    order_by: list[OrderByClause] = field(default_factory=list)
    limit: Optional[int] = None
    join_path: Optional[JoinPath] = None
    confidence: float = 1.0


@dataclass
class BuildResult:
    """Resultado do query builder."""
    sql: str
    params: dict  # parâmetros nomeados {"p0": val, "p1": val, ...}
    tables_used: list[str]

    def to_dict(self) -> dict:
        return {"sql": self.sql, "params": self.params, "tables_used": self.tables_used}


# ─── API pública ───────────────────────────────────────────────────────────────

def build_sql(plan: V2Plan, digest: DBDigest) -> Optional[BuildResult]:
    """
    Constrói SQL a partir de um V2Plan validado contra o digest.

    Retorna None se:
    - confidence < _MIN_CONFIDENCE
    - Alguma tabela no plano não existe no digest
    - intent não é suportado

    Args:
        plan  : Plano estruturado com intent, tables, filters, etc.
        digest: DBDigest cadastrado para o agente.

    Returns:
        BuildResult(sql, params, tables_used) ou None.
    """
    if plan.confidence < _MIN_CONFIDENCE:
        logger.debug(
            "[query_builder] confiança insuficiente: %.2f < %.2f",
            plan.confidence,
            _MIN_CONFIDENCE,
        )
        return None

    # Validar tabelas
    validated_tables: list[str] = []
    for t in plan.tables:
        td = get_table_from_digest(digest, t)
        if td is None:
            logger.debug("[query_builder] tabela '%s' não existe no digest — abort", t)
            return None
        validated_tables.append(td.name)  # usa o nome canônico do digest

    intent = plan.intent.upper()

    if intent == "SELECT":
        return _build_select(plan, validated_tables, digest)
    elif intent == "COUNT":
        return _build_count(plan, validated_tables, digest)
    elif intent == "SELECT_JOIN":
        return _build_select_join(plan, validated_tables, digest)
    elif intent == "COUNT_JOIN":
        return _build_count_join(plan, validated_tables, digest)
    else:
        logger.debug("[query_builder] intent desconhecido: %s", intent)
        return None


# ─── Builders internos ────────────────────────────────────────────────────────

def _build_select(
    plan: V2Plan,
    tables: list[str],
    digest: DBDigest,
) -> Optional[BuildResult]:
    table = tables[0]
    known_cols = _column_names(digest, table)
    params: dict = {}

    where_clause, where_params = _build_where(plan.filters, known_cols, table, params)

    order_clause = _build_order_by(plan.order_by, known_cols, table)
    limit = min(plan.limit or _DEFAULT_LIMIT, _HARD_MAX_LIMIT)

    # Definir colunas da projeção
    projection = "*"
    if plan.columns:
        valid_cols = [f"`{c}`" for c in plan.columns if c.lower() in {kc.lower() for kc in known_cols}]
        if valid_cols:
            projection = ", ".join(valid_cols)
            
    sql_parts = [f"SELECT {projection} FROM `{table}`"]
    if where_clause:
        sql_parts.append(f"WHERE {where_clause}")
    if order_clause:
        sql_parts.append(f"ORDER BY {order_clause}")
    sql_parts.append(f"LIMIT {limit}")

    return BuildResult(
        sql=" ".join(sql_parts),
        params=params,
        tables_used=[table],
    )


def _build_count(
    plan: V2Plan,
    tables: list[str],
    digest: DBDigest,
) -> Optional[BuildResult]:
    table = tables[0]
    known_cols = _column_names(digest, table)
    params: dict = {}

    where_clause, where_params = _build_where(plan.filters, known_cols, table, params)

    sql_parts = [f"SELECT COUNT(*) AS total FROM `{table}`"]
    if where_clause:
        sql_parts.append(f"WHERE {where_clause}")

    return BuildResult(
        sql=" ".join(sql_parts),
        params=params,
        tables_used=[table],
    )


def _build_select_join(
    plan: V2Plan,
    tables: list[str],
    digest: DBDigest,
) -> Optional[BuildResult]:
    if not plan.join_path or len(tables) < 2:
        logger.debug("[query_builder] SELECT_JOIN sem join_path ou menos de 2 tabelas")
        return None

    jp = plan.join_path
    left = jp.left_table
    right = jp.right_table
    lc = jp.left_col
    rc = jp.right_col

    # Validar nomes de coluna na FK — seguros pois vieram do digest
    left_cols = _column_names(digest, left)
    right_cols = _column_names(digest, right)

    if lc.lower() not in {c.lower() for c in left_cols}:
        logger.debug("[query_builder] coluna FK esquerda '%s.%s' não validada", left, lc)
        return None
    if rc.lower() not in {c.lower() for c in right_cols}:
        logger.debug("[query_builder] coluna FK direita '%s.%s' não validada", right, rc)
        return None

    # Filtros — combinam colunas das duas tabelas
    combined_cols = left_cols | right_cols
    params: dict = {}
    where_clause, _ = _build_where(plan.filters, combined_cols, None, params)

    order_clause = _build_order_by(plan.order_by, combined_cols, None)
    limit = min(plan.limit or _DEFAULT_LIMIT, _HARD_MAX_LIMIT)

    # Projeção no JOIN
    projection = f"`{left}`.*, `{right}`.*"
    if plan.columns:
        valid_cols = []
        for c in plan.columns:
            # Tentar achar a tabela da coluna
            if c.lower() in {kc.lower() for kc in left_cols}:
                valid_cols.append(f"`{left}`.`{c}`")
            elif c.lower() in {kc.lower() for kc in right_cols}:
                valid_cols.append(f"`{right}`.`{c}`")
        if valid_cols:
            projection = ", ".join(valid_cols)

    sql_parts = [
        f"SELECT {projection}",
        f"FROM `{left}`",
        f"INNER JOIN `{right}` ON `{left}`.`{lc}` = `{right}`.`{rc}`",
    ]
    if where_clause:
        sql_parts.append(f"WHERE {where_clause}")
    if order_clause:
        sql_parts.append(f"ORDER BY {order_clause}")
    sql_parts.append(f"LIMIT {limit}")

    return BuildResult(
        sql="\n".join(sql_parts),
        params=params,
        tables_used=[left, right],
    )


def _build_count_join(
    plan: V2Plan,
    tables: list[str],
    digest: DBDigest,
) -> Optional[BuildResult]:
    if not plan.join_path or len(tables) < 2:
        return None

    jp = plan.join_path
    left = jp.left_table
    right = jp.right_table
    lc = jp.left_col
    rc = jp.right_col

    left_cols = _column_names(digest, left)
    right_cols = _column_names(digest, right)
    combined_cols = left_cols | right_cols

    params: dict = {}
    where_clause, _ = _build_where(plan.filters, combined_cols, None, params)

    sql_parts = [
        f"SELECT COUNT(*) AS total",
        f"FROM `{left}`",
        f"INNER JOIN `{right}` ON `{left}`.`{lc}` = `{right}`.`{rc}`",
    ]
    if where_clause:
        sql_parts.append(f"WHERE {where_clause}")

    return BuildResult(
        sql="\n".join(sql_parts),
        params=params,
        tables_used=[left, right],
    )


# ─── WHERE builder ────────────────────────────────────────────────────────────

def _build_where(
    filters: list[QueryFilter],
    known_cols: set[str],
    table_prefix: Optional[str],
    params: dict,
) -> tuple[str, dict]:
    """
    Constrói a cláusula WHERE a partir dos filtros.

    Somente filtros cujos campos existam nas colunas conhecidas são incluídos.
    Campos desconhecidos são silenciosamente descartados (não param o query).
    Valores nunca são interpolados — usamos parâmetros nomeados %(pN)s.

    Args:
        filters     : Lista de QueryFilter extraídos pelo filter_parser.
        known_cols  : Conjunto de colunas válidas (do digest).
        table_prefix: Prefixo de tabela para backtick (ou None para sem prefixo).
        params      : Dict mutável que recebe os parâmetros nomeados (saída).

    Returns:
        (where_sql_str, params) — params é o mesmo dict passado, preenchido.
    """
    parts: list[str] = []

    # Para comparação case-insensitive
    known_lower = {c.lower(): c for c in known_cols}

    for f in filters:
        canon = known_lower.get(f.field.lower())
        if canon is None:
            logger.debug(
                "[query_builder] campo '%s' não encontrado no digest — filtro ignorado",
                f.field,
            )
            continue

        col_ref = f"`{table_prefix}`.`{canon}`" if table_prefix else f"`{canon}`"
        param_key = f"p{len(params)}"

        if f.op in ("IS NULL", "IS NOT NULL"):
            parts.append(f"{col_ref} {f.op}")
        elif f.op == "LIKE":
            parts.append(f"{col_ref} LIKE %({param_key})s")
            params[param_key] = f.value
        else:
            parts.append(f"{col_ref} {f.op} %({param_key})s")
            params[param_key] = f.value

    return (" AND ".join(parts), params)


# ─── ORDER BY builder ─────────────────────────────────────────────────────────

def _build_order_by(
    order_clauses: list[OrderByClause],
    known_cols: set[str],
    table_prefix: Optional[str],
) -> str:
    known_lower = {c.lower(): c for c in known_cols}
    parts: list[str] = []
    for o in order_clauses:
        canon = known_lower.get(o.field.lower())
        if canon is None:
            logger.debug("[query_builder] campo ORDER BY '%s' ignorado — não no digest", o.field)
            continue
        direction = "DESC" if o.direction.lower() == "desc" else "ASC"
        col_ref = f"`{table_prefix}`.`{canon}`" if table_prefix else f"`{canon}`"
        parts.append(f"{col_ref} {direction}")
    return ", ".join(parts)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _column_names(digest: DBDigest, table_name: str) -> set[str]:
    """Retorna conjunto de nomes de coluna para uma tabela do digest."""
    td = get_table_from_digest(digest, table_name)
    if td is None:
        return set()
    return {c.name for c in td.columns}
