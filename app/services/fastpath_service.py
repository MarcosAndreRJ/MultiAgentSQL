"""
FastPath Service: execução determinística de queries simples, sem LLM.

Estende os intents do fast_path_router incluindo LIST_RECORDS e combina
detecção + execução em um único serviço coeso e testável.

Intents suportados:
  COUNT_TABLE       → SELECT COUNT(*) AS total FROM `table`
  DESCRIBE_TABLE    → instrospect describe_table
  SHOW_CREATE_TABLE → SHOW CREATE TABLE `table`
  LIST_TABLES       → introspect list_tables
  LIST_VIEWS        → introspect list_views
  LIST_TRIGGERS     → introspect list_triggers
  LIST_RECORDS      → SELECT * FROM `table` LIMIT 50   ← NOVO

Regras de segurança:
  - Nunca executa SQL destrutivo (DELETE, DROP, UPDATE, ALTER, TRUNCATE)
  - Valida existência da tabela antes de qualquer query de dados
  - Nomes de tabela backtick-escaped para neutralizar SQL injection
  - Retorna None em qualquer falha → fallback para LLM
  - Nenhuma mutação de dados é realizada por esta camada
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from app.core import session_store
from app.core.logger import get_logger
from app.schemas.agent import AgentConfig
from app.schemas.chat import Session
from app.schemas.execution import DBExecuteRequest
from app.services.fast_path_router import (
    FastPathIntentResult,
    FastPathIntentType,
    detect_fast_path_intent,
)
from app.tools import db_execute, db_introspection

logger = get_logger("fastpath_service")

# ─── Constante de intent extra ─────────────────────────────────────────────────
LIST_RECORDS_INTENT = "LIST_RECORDS"

# Palavras de tabela que nunca devem ser aceitas como nome real
_IGNORE_WORDS = frozenset({
    "tabelas", "views", "triggers", "procedures", "functions",
    "tudo", "banco", "database", "objetos", "registros", "dados",
})

# Padrão para extrair nome de tabela de mensagens
_TABLE_TOKEN_RE = r'(?:```|`|"|\')?([a-zA-Z0-9_]+)(?:```|`|"|\')?'

# Palavras que indicam operações destrutivas — bloqueiam o fast-path
_DESTRUCTIVE_RE = re.compile(
    r'\b(delete|drop|update|insert|alter|truncate)\b', re.IGNORECASE
)


# ─── Resultado ─────────────────────────────────────────────────────────────────

@dataclass
class FastPathResult:
    """Resultado de uma execução fast-path bem-sucedida."""
    intent: str
    response: str
    sql: Optional[str] = None
    table_name: Optional[str] = None
    rows: list[dict] = field(default_factory=list)
    status: str = "completed"
    execution_source: str = "fast_path"
    metadata: dict = field(default_factory=dict)


# ─── Detecção ──────────────────────────────────────────────────────────────────

def _detect_list_records(text_clean: str, original: str) -> Optional[str]:
    """
    Detecta padrões de listagem de registros de uma tabela específica.
    Retorna o nome da tabela (com casing original) ou None.

    Padrões suportados:
      "listar Dica"              → Dica
      "mostrar registros Projeto" → Projeto
      "ver ClientePF"            → ClientePF
      "select * from usuarios"   → usuarios
      "list orders"              → orders

    Args:
        text_clean: versão lowercase/sem pontuação final (para matching)
        original:   versão original da mensagem (para preservar casing na extração)
    """
    # Não confundir com "listar tabelas" (LIST_TABLES)
    if re.search(r'\btabelas\b', text_clean):
        return None

    patterns = [
        # Verbos PT-BR/EN seguidos de opcional "registros" + nome de tabela
        rf'(?:listar?|mostrar|ver|exibir|selecionar)(?:\s+(?:os\s+|as\s+)?registros?)?\s+{_TABLE_TOKEN_RE}$',
        # SELECT * [FROM] table
        rf'select\s+\*(?:\s+from)?\s+{_TABLE_TOKEN_RE}$',
        # list/show simples em inglês (ex: "list orders")
        rf'^(?:list|show)\s+{_TABLE_TOKEN_RE}$',
    ]

    # Preparar versão original sem pontuação final para extração com casing correto
    original_clean = re.sub(r'[?!.]+$', '', original.strip()).strip()

    for pattern in patterns:
        # Matching contra lowercase para case-insensitive
        m_lower = re.search(pattern, text_clean)
        if m_lower:
            table_lower = m_lower.group(1)
            if table_lower.lower() in _IGNORE_WORDS:
                continue
            # Extrair com casing original usando re.IGNORECASE no texto original
            m_orig = re.search(pattern, original_clean, re.IGNORECASE)
            if m_orig:
                return m_orig.group(1)
            # Fallback: retornar com lowercase se não encontrou no original
            return table_lower

    return None


def detect_intent(message: str) -> tuple[str | None, str | None]:
    """
    Detecta o intent fast-path da mensagem, incluindo LIST_RECORDS.

    Returns:
        (intent_name, table_name) — ou (None, None) se não reconhecido.

    Fluxo interno:
      1. Bloquear palavras destrutivas
      2. Verificar LIST_RECORDS antes do router padrão
      3. Delegar ao fast_path_router para os demais intents
    """
    text = message.strip().lower()
    text_clean = re.sub(r'[?!.]+$', '', text).strip()

    # Bloquear operações destrutivas — exceção: "show create table X" contém "create"
    found = _DESTRUCTIVE_RE.findall(text_clean)
    if found:
        found_set = {w.lower() for w in found}
        # "show create table X" → create é o único keyword e o contexto é seguro
        if not (found_set == {"create"} and "show create" in text_clean):
            logger.debug(f"[FASTPATH] Bloqueado por keywords destrutivos: {found_set}")
            return None, None

    # LIST_RECORDS tem prioridade para não conflitar com LIST_TABLES
    # Passa original para preservar casing do nome da tabela
    table = _detect_list_records(text_clean, message)
    if table:
        return LIST_RECORDS_INTENT, table

    # Delegar ao router existente para os demais intents
    result: FastPathIntentResult = detect_fast_path_intent(message)
    if result.matched:
        return result.intent.value, result.table_name

    return None, None


# ─── Ponto de entrada principal ────────────────────────────────────────────────

async def execute_fast_path(
    agent: AgentConfig,
    message: str,
    session: Session,
) -> Optional[FastPathResult]:
    """
    Tenta resolver a mensagem via fast-path (sem LLM).

    Retorna:
        FastPathResult — se o intent foi reconhecido e executado com sucesso.
        None — se o intent não foi reconhecido ou houve falha (→ LLM assume).
    """
    intent, table = detect_intent(message)
    if intent is None:
        return None

    logger.info(f"[FASTPATH] intent={intent} | tabela={table} | agente={agent.id}")

    try:
        # ──── LIST_RECORDS ────────────────────────────────────────────────
        if intent == LIST_RECORDS_INTENT:
            return await _exec_list_records(agent, session, table)

        # ──── LIST_TABLES ─────────────────────────────────────────────────
        if intent == FastPathIntentType.LIST_TABLES:
            return await _exec_list_tables(agent, session)

        # ──── LIST_VIEWS ──────────────────────────────────────────────────
        if intent == FastPathIntentType.LIST_VIEWS:
            return await _exec_list_views(agent, session)

        # ──── LIST_TRIGGERS ───────────────────────────────────────────────
        if intent == FastPathIntentType.LIST_TRIGGERS:
            return await _exec_list_triggers(agent, session)

        # Para intents que dependem de tabela válida — validar antes de executar
        if table and not await _table_exists(agent, table):
            logger.warning(f"[FASTPATH] Tabela '{table}' não encontrada → fallback LLM")
            return None

        # ──── DESCRIBE_TABLE ──────────────────────────────────────────────
        if intent == FastPathIntentType.DESCRIBE_TABLE:
            return await _exec_describe_table(agent, session, table)

        # ──── SHOW_CREATE_TABLE ───────────────────────────────────────────
        if intent == FastPathIntentType.SHOW_CREATE_TABLE:
            return await _exec_show_create_table(agent, session, table)

        # ──── COUNT_TABLE ─────────────────────────────────────────────────
        if intent == FastPathIntentType.COUNT_TABLE:
            return await _exec_count_table(agent, session, table)

    except Exception as exc:  # pragma: no cover
        logger.error(f"[FASTPATH] Erro no intent '{intent}': {exc}", exc_info=True)
        return None

    return None


# ─── Handlers individuais ──────────────────────────────────────────────────────

async def _table_exists(agent: AgentConfig, table: str) -> bool:
    """Verifica se a tabela existe no banco usando DESCRIBE."""
    res = db_introspection.introspect(agent, "describe_table", table)
    return bool(res.success and res.rows)


async def _exec_list_records(
    agent: AgentConfig, session: Session, table: str
) -> Optional[FastPathResult]:
    if not await _table_exists(agent, table):
        logger.warning(f"[FASTPATH] Tabela '{table}' inexistente → fallback LLM")
        return None

    sql = f"SELECT * FROM `{table}` LIMIT 50"
    req = DBExecuteRequest(sql=sql, mode="read")
    res = db_execute.execute(req, agent)
    if not res.success:
        logger.warning(f"[FASTPATH] Falha ao listar '{table}': {res.error}")
        return None

    formatted = _format_rows(res.rows, res.columns)
    text = (
        f"[RESUMO]\nListei os registros da tabela `{table}` (máximo 50 linhas).\n\n"
        f"[SQL]\n```sql\n{sql};\n```\n\n"
        f"[RESULTADO]\n{formatted}\n\n"
        f"[STATUS]\nExecutado com sucesso"
    )
    _store(session, text)
    return FastPathResult(
        intent=LIST_RECORDS_INTENT,
        response=text,
        sql=sql,
        table_name=table,
        rows=res.rows,
    )


async def _exec_list_tables(
    agent: AgentConfig, session: Session
) -> Optional[FastPathResult]:
    res = db_introspection.introspect(agent, "list_tables")
    if not res.success:
        return None
    names = [list(r.values())[0] for r in res.rows if r]
    session_store.update_context(session.session_id, recent_tables=names[:10])
    text = (
        f"[RESUMO]\nListei as tabelas do banco de dados.\n\n"
        f"[RESULTADO]\n{', '.join(str(n) for n in names)}\n\n"
        f"[STATUS]\nExecutado com sucesso"
    )
    _store(session, text)
    return FastPathResult(intent=FastPathIntentType.LIST_TABLES.value, response=text)


async def _exec_list_views(
    agent: AgentConfig, session: Session
) -> Optional[FastPathResult]:
    res = db_introspection.introspect(agent, "list_views")
    if not res.success:
        return None
    names = [list(r.values())[0] for r in res.rows if r]
    session_store.update_context(session.session_id, recent_views=names[:5])
    body = ', '.join(str(n) for n in names) if names else 'Nenhuma view encontrada'
    text = (
        f"[RESUMO]\nListei as views do banco de dados.\n\n"
        f"[RESULTADO]\n{body}\n\n"
        f"[STATUS]\nExecutado com sucesso"
    )
    _store(session, text)
    return FastPathResult(intent=FastPathIntentType.LIST_VIEWS.value, response=text)


async def _exec_list_triggers(
    agent: AgentConfig, session: Session
) -> Optional[FastPathResult]:
    res = db_introspection.introspect(agent, "list_triggers")
    if not res.success:
        return None
    names = [r.get("Trigger", "") for r in res.rows if r]
    session_store.update_context(session.session_id, recent_triggers=names[:5])
    body = ', '.join(str(n) for n in names) if names else 'Nenhuma trigger encontrada'
    text = (
        f"[RESUMO]\nListei as triggers do banco de dados.\n\n"
        f"[RESULTADO]\n{body}\n\n"
        f"[STATUS]\nExecutado com sucesso"
    )
    _store(session, text)
    return FastPathResult(intent=FastPathIntentType.LIST_TRIGGERS.value, response=text)


async def _exec_describe_table(
    agent: AgentConfig, session: Session, table: str
) -> Optional[FastPathResult]:
    res = db_introspection.introspect(agent, "describe_table", table)
    if not res.success:
        return None
    formatted = _format_rows(res.rows, res.columns)
    sql_str = f"DESCRIBE `{table}`"
    text = (
        f"[RESUMO]\nDescrevi a estrutura da tabela `{table}`.\n\n"
        f"[SQL]\n```sql\n{sql_str};\n```\n\n"
        f"[RESULTADO]\n{formatted}\n\n"
        f"[STATUS]\nExecutado com sucesso"
    )
    _store(session, text)
    return FastPathResult(
        intent=FastPathIntentType.DESCRIBE_TABLE.value,
        response=text,
        sql=sql_str,
        table_name=table,
        rows=res.rows,
    )


async def _exec_show_create_table(
    agent: AgentConfig, session: Session, table: str
) -> Optional[FastPathResult]:
    sql_str = f"SHOW CREATE TABLE `{table}`"
    req = DBExecuteRequest(sql=sql_str, mode="read")
    res = db_execute.execute(req, agent)
    if not res.success or not res.rows:
        return None
    ddl = list(res.rows[0].values())[1]  # Coluna "Create Table"
    text = (
        f"[RESUMO]\nExtraí o DDL da tabela `{table}`.\n\n"
        f"[SQL]\n```sql\n{sql_str};\n```\n\n"
        f"[RESULTADO]\n```sql\n{ddl}\n```\n\n"
        f"[STATUS]\nExecutado com sucesso"
    )
    _store(session, text)
    return FastPathResult(
        intent=FastPathIntentType.SHOW_CREATE_TABLE.value,
        response=text,
        sql=sql_str,
        table_name=table,
    )


async def _exec_count_table(
    agent: AgentConfig, session: Session, table: str
) -> Optional[FastPathResult]:
    sql_str = f"SELECT COUNT(*) AS total FROM `{table}`"
    req = DBExecuteRequest(sql=sql_str, mode="read")
    res = db_execute.execute(req, agent)
    if not res.success:
        return None
    total = list(res.rows[0].values())[0] if res.rows else 0
    text = (
        f"[RESUMO]\nContei os registros da tabela `{table}`.\n\n"
        f"[SQL]\n```sql\n{sql_str};\n```\n\n"
        f"[RESULTADO]\n{total} registro(s) encontrado(s).\n\n"
        f"[STATUS]\nExecutado com sucesso"
    )
    _store(session, text)
    return FastPathResult(
        intent=FastPathIntentType.COUNT_TABLE.value,
        response=text,
        sql=sql_str,
        table_name=table,
    )


# ─── Utilidades internas ───────────────────────────────────────────────────────

def _store(session: Session, text: str) -> None:
    """Persiste a resposta no histórico da sessão."""
    session_store.add_message(session.session_id, "assistant", text)


def _format_rows(
    rows: list[dict],
    columns: Optional[list[str]] = None,
    max_rows: int = 50,
) -> str:
    """Formata lista de linhas como tabela texto simples."""
    if not rows:
        return "(sem resultados)"

    display = rows[:max_rows]
    cols = columns or list(display[0].keys())
    if not cols:
        return str(display)

    # Largura máxima de 50 chars por célula para evitar output gigante
    widths = {col: len(str(col)) for col in cols}
    for row in display:
        for col in cols:
            widths[col] = max(widths[col], min(len(str(row.get(col, "NULL"))), 50))

    header = " | ".join(str(col).ljust(widths[col]) for col in cols)
    separator = "-+-".join("-" * widths[col] for col in cols)
    lines = [header, separator]

    for row in display:
        line = " | ".join(
            str(row.get(col, "NULL"))[:50].ljust(widths[col]) for col in cols
        )
        lines.append(line)

    if len(rows) > max_rows:
        lines.append(f"... ({len(rows) - max_rows} linha(s) omitida(s))")

    return "\n".join(lines)
