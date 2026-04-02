"""
FastPath V2 Service: motor de consulta semântico-determinístico guiado pelo DB Digest.

Responsabilidades:
- Interceptar mensagens antes do LLM quando o digest estiver disponível
- Identificar tabelas mencionadas na mensagem (via digest como whitelist)
- Extrair filtros, limites e ordenações com filter_parser
- Resolver JOINs via join_resolver quando 2 tabelas são identificadas
- Construir SQL seguro e parametrizado via query_builder
- Executar de forma síncrona e retornar FastPathResult
- Registrar analytics de tabelas e intents usados
- Retornar None (com motivo logado) para fallback ao V1/LLM

Fluxo:
  message
    ↓ resolve_aliases
    ↓ _find_tables (whitelist = digest)
    ↓ parse_slots (filter_parser)
    ↓ _classify_intent (SELECT | COUNT)
    ↓ V2Plan → query_builder.build_sql()
    ↓ db_execute.execute()
    ↓ format_response()
    → FastPathResult ou None

Segurança:
- Somente SELECT e COUNT — nunca operações destrutivas
- Todos os nomes de tabela e coluna validados contra o digest
- Valores parametrizados (%s) — nunca interpolados no SQL
- Digest obrigatório — sem digest, V2 é transparente
"""
from __future__ import annotations

import re
from typing import Optional

from app.core.logger import get_logger
from app.schemas.agent import AgentConfig
from app.schemas.chat import Session
from app.schemas.execution import DBExecuteRequest
from app.services import analytics_service
from app.services.alias_service import resolve_message_aliases
from app.services.digest_service import load_digest
from app.services.fastpath_service import FastPathResult
from app.services.filter_parser import parse_slots
from app.services.join_resolver import (
    find_join_chain,
    get_table_from_digest,
    table_exists_in_digest,
)
from app.services.query_builder import V2Plan, build_sql
from app.tools import db_execute

logger = get_logger("fastpath_v2")

# ─── Constantes ───────────────────────────────────────────────────────────────

# Palavras-chave que indicam intent COUNT
_COUNT_KEYWORDS = re.compile(
    r'\b(quantos?|count|contar|total\s+de|n[uú]mero\s+de|qt[de]|quantidade\s+de)\b',
    re.IGNORECASE,
)

# Palavras-chave de queries de schema/metadata — devemos deixar o V1 tratar
_SCHEMA_KEYWORDS = re.compile(
    r'\b(descrev[ae]|describe|estrutura|show\s+create|colunas?|campos?|triggers?|'
    r'procedures?|fun[cç][aã]o|fun[cç][oõ]es|views?\s+desta|quais\s+tabelas?|'
    r'list[ae]\s+tabelas?|list\s+tables?|quais\s+views?|listar\s+views?|'
    r'listar\s+triggers?|esquema|schema|metadata)\b',
    re.IGNORECASE,
)

# Palavras-chave destrutivas — bloquear imediatamente
_DESTRUCTIVE_KEYWORDS = re.compile(
    r'\b(delete|drop|update|insert|alter|truncate|create|grant|revoke|'
    r'apagar|deletar|remover|excluir|atualizar|inserir|criar\s+tabela)\b',
    re.IGNORECASE,
)

# Indicadores de que a mensagem tem dados (filtros), não só nome de tabela
_DATA_QUERY_SIGNALS = re.compile(
    r'\b(onde|where|com\b|having|cujo|cujas?|cuja|'
    r'maior|menor|igual|diferente|contém|contain|like|'
    r'ordenad[ao]|order\s+by|primeiros?|[uú]ltimos?|limite|limit|top\b|'
    r'status|ativo|inativo|id\b|nome\b|data\b)\b',
    re.IGNORECASE,
)

# Tamanho máximo de palavras para buscar tabelas (bi-gramas incluídos)
_MAX_NGRAM = 2


# ─── API Pública ──────────────────────────────────────────────────────────────

async def execute(
    agent: AgentConfig,
    message: str,
    session: Session,
) -> Optional[FastPathResult]:
    """
    Tenta resolver a mensagem sem LLM usando o DB Digest como guia.

    Args:
        agent  : Configuração do agente (contém agent_id, database, etc.)
        message: Mensagem bruta do usuário.
        session: Sessão de chat atual.

    Returns:
        FastPathResult se resolvido, None para fallback ao V1/LLM.
    """
    agent_id = agent.id

    # 1. Verificações rápidas de segurança e viabilidade
    if _DESTRUCTIVE_KEYWORDS.search(message):
        logger.debug("[V2] bloqueado: palavra destrutiva detectada")
        return None

    if _SCHEMA_KEYWORDS.search(message):
        logger.debug("[V2] passando para V1: query de schema/metadata detectada")
        return None

    # 2. Carregar digest — sem digest, V2 é transparente
    digest = load_digest(agent_id)
    if digest is None:
        logger.debug("[V2] sem digest para agente=%s — passando para V1", agent_id)
        return None

    if not digest.tables and not digest.views:
        logger.debug("[V2] digest vazio para agente=%s", agent_id)
        return None

    # 3. Resolver aliases (@token → nome_real) antes de buscar tabelas
    resolved_msg, alias_hits = resolve_message_aliases(agent_id, message)

    # 4. Encontrar tabelas mencionadas na mensagem (whitelist = digest)
    tables_found = _find_tables_in_message(resolved_msg, digest)
    if not tables_found:
        logger.debug("[V2] nenhuma tabela identificada em: %r", resolved_msg[:80])
        return None

    if len(tables_found) > 2:
        logger.debug("[V2] %d tabelas encontradas — muito complexo para V2", len(tables_found))
        return None

    # 5. Verificar se a mensagem é sobre dados (não só nome de tabela)
    #    Para 1 tabela sem sinais de dados isso pode ser LIST_RECORDS do V1 — deixamos cair
    is_data_query = bool(_DATA_QUERY_SIGNALS.search(resolved_msg))
    is_count_query = bool(_COUNT_KEYWORDS.search(resolved_msg))

    if len(tables_found) == 1 and not is_data_query and not is_count_query:
        # Provavelmente "mostre registros de X" — V1 LIST_RECORDS trata melhor
        logger.debug("[V2] sem sinais de dados para tabela única — passando para V1")
        return None

    # 6. Extrair filtros, limite e ordenação
    slots = parse_slots(resolved_msg)

    # 7. Classificar intent
    intent = "COUNT" if is_count_query else "SELECT"

    # 8. Resolver JOIN se 2 tabelas
    join_path = None
    if len(tables_found) == 2:
        chain = find_join_chain(digest, tables_found)
        if chain is None:
            logger.debug("[V2] não foi possível resolver JOIN entre %s — passando para V1/LLM", tables_found)
            return None
        join_path = chain[0]
        intent = f"{intent}_JOIN"

    # 9. Construir plano com confiança
    confidence = _calculate_confidence(tables_found, slots, join_path, digest)

    plan = V2Plan(
        intent=intent,
        tables=tables_found,
        filters=slots.filters,
        order_by=slots.order_by,
        limit=slots.limit,
        join_path=join_path,
        confidence=confidence,
    )

    # 10. Construir SQL
    build_result = build_sql(plan, digest)
    if build_result is None:
        logger.info(
            "[V2] query_builder recusou o plano (confiança=%.2f, intent=%s) — fallback",
            confidence,
            intent,
        )
        return None

    # 11. Executar query
    req = DBExecuteRequest(
        sql=build_result.sql,
        params=build_result.params,   # dict de parâmetros nomeados
        mode="read",
        dry_run=False,
    )

    try:
        result = db_execute.execute(req, agent)
    except Exception as exc:
        logger.error("[V2] erro na execução: %s", exc)
        return None

    if not result.success:
        logger.info("[V2] query falhou: %s — fallback para V1/LLM", result.error)
        return None

    # 12. Registrar analytics
    try:
        analytics_service.record_tables_mentioned(agent_id, build_result.tables_used)
        analytics_service.record_intent(agent_id, f"V2_{intent}")
        if alias_hits:
            analytics_service.record_aliases_used(agent_id, alias_hits)
    except Exception as exc:
        logger.warning("[V2] falha no registro de analytics: %s", exc)

    # 13. Salvar Padrão Semântico (Memória)
    try:
        from app.services.semantic.pattern_store import save_pattern
        from app.schemas.semantic import PatternFilter
        from app.services.query_builder import _column_names
        
        mem_filters = []
        p_idx = 0
        left_cols = _column_names(digest, tables_found[0]) if len(tables_found) > 0 else set()
        right_cols = _column_names(digest, tables_found[1]) if len(tables_found) > 1 else set()
        combined_cols = {c.lower(): c for c in (left_cols | right_cols)}
        
        for f in slots.filters:
            if f.field.lower() in combined_cols:
                mem_filters.append(PatternFilter(
                    field=combined_cols[f.field.lower()], 
                    op=f.op, 
                    slot_name=f"p{p_idx}", 
                    slot_value=f.value
                ))
                p_idx += 1
                
        save_pattern(
            agent_id=agent_id,
            intent_family=intent,
            tables=build_result.tables_used,
            filters=mem_filters,
            sql_template=build_result.sql,
            user_message=message,
            limit=slots.limit,
            order_by=[{"field": o.field, "direction": o.direction} for o in slots.order_by] if slots.order_by else None,
            join_path={"left_table": join_path.left_table, "left_col": join_path.left_col, "right_table": join_path.right_table, "right_col": join_path.right_col} if join_path else None
        )
    except Exception as exc:
        logger.warning("[V2] falha ao salvar pattern semântico: %s", exc)

    # 13. Formatar resposta
    response_text = _format_response(intent, build_result, result, plan)

    return FastPathResult(
        intent=f"V2_{intent}",
        response=response_text,
        sql=build_result.sql,
        table_name=", ".join(build_result.tables_used),
        rows=result.rows or [],
        status="completed",
    )


# ─── Detecção de tabelas ──────────────────────────────────────────────────────

def _find_tables_in_message(text: str, digest) -> list[str]:
    """
    Encontra tabelas mencionadas na mensagem usando o digest como whitelist.

    Estratégia:
    - Tokeniza a mensagem em palavras
    - Testa uni-gramas e bi-gramas contra o índice de tabelas
    - Bi-gramas têm prioridade sobre uni-gramas

    Retorna lista ordenada pela primeira menção (sem duplicatas).
    """
    # Construir índice: nome_lower → nome_canônico
    all_tables = list(digest.tables) + list(digest.views)
    index: dict[str, str] = {t.name.lower(): t.name for t in all_tables}

    # Extrair tokens alphabéticos (sem números isolados)
    tokens = re.findall(r'[A-Za-z_][A-Za-z0-9_]*', text)

    found: list[str] = []
    seen: set[str] = set()
    skip_indices: set[int] = set()

    # Primeiro: bi-gramas (prioridade para nomes compostos tipo "pessoa_fisica")
    for i in range(len(tokens) - 1):
        bigram = f"{tokens[i]}_{tokens[i+1]}"
        if bigram.lower() in index:
            canon = index[bigram.lower()]
            if canon not in seen:
                found.append(canon)
                seen.add(canon)
                skip_indices.add(i)
                skip_indices.add(i + 1)

    # Depois: uni-gramas não cobertos por bi-gramas
    for i, token in enumerate(tokens):
        if i in skip_indices:
            continue
        tl = token.lower()
        if tl in index:
            canon = index[tl]
            if canon not in seen:
                found.append(canon)
                seen.add(canon)

    return found


# ─── Cálculo de confiança ────────────────────────────────────────────────────

def _calculate_confidence(
    tables: list[str],
    slots,
    join_path,
    digest,
) -> float:
    """
    Calcula a confiança do plano V2 (0.0 - 1.0).

    Base: 0.85 para 1 tabela, 0.90 para JOIN resolvido.
    Penaliza se nenhum filtro e nenhum limit/order especificado.
    """
    if not tables:
        return 0.0

    base = 0.90 if join_path else 0.85

    # Verificar proporção de filtros com colunas válidas no digest
    if slots.filters:
        valid_filters = 0
        for f in slots.filters:
            td = get_table_from_digest(digest, tables[0])
            if td and any(c.name.lower() == f.field.lower() for c in td.columns):
                valid_filters += 1
        ratio = valid_filters / len(slots.filters)
        # Se nenhum filtro é validável, penaliza leve (ainda pode executar sem filtros)
        if ratio == 0:
            base -= 0.10

    return round(base, 2)


# ─── Formatação de resposta ───────────────────────────────────────────────────

def _format_response(intent: str, build_result, exec_result, plan: V2Plan) -> str:
    """Formata a resposta no padrão [RESUMO]/[SQL]/[RESULTADO]/[STATUS]."""
    tables_str = ", ".join(f"`{t}`" for t in build_result.tables_used)
    intent_upper = intent.upper()

    # Resumo
    if "COUNT" in intent_upper:
        total = exec_result.rows[0].get("total", 0) if exec_result.rows else 0
        summary = f"Total de registros em {tables_str}: **{total}**"
        if plan.filters:
            filter_desc = ", ".join(
                f"{f.field} {f.op} {f.value!r}" for f in plan.filters
            )
            summary += f"\nFiltros aplicados: {filter_desc}"
    else:
        n = len(exec_result.rows or [])
        limit_used = plan.limit or 50
        summary = f"Encontrado(s) **{n}** registro(s) em {tables_str}"
        if n == limit_used:
            summary += f" (limite de {limit_used} aplicado)"
        if plan.filters:
            filter_desc = ", ".join(
                f"{f.field} {f.op} {f.value!r}" for f in plan.filters
            )
            summary += f"\nFiltros aplicados: {filter_desc}"

    # Bloco SQL
    sql_block = f"```sql\n{build_result.sql}\n```"

    # Bloco de dados
    if "COUNT" in intent_upper:
        data_block = _format_count_result(exec_result.rows)
    else:
        data_block = _format_rows_result(exec_result.rows, exec_result.columns)

    truncated_note = ""
    if getattr(exec_result, "truncated", False):
        truncated_note = "\n> ⚠️ Resultado truncado. Use um filtro mais específico."

    return (
        f"[RESUMO]\n{summary}\n\n"
        f"[SQL]\n{sql_block}\n\n"
        f"[RESULTADO]\n{data_block}{truncated_note}\n\n"
        f"[STATUS] completed"
    )


def _format_count_result(rows: list[dict]) -> str:
    if not rows:
        return "_Sem resultados._"
    return f"**{rows[0].get('total', 0)}** registro(s)."


def _format_rows_result(rows: list[dict], columns: list[str]) -> str:
    if not rows:
        return "_Nenhum registro encontrado._"

    cols = columns or (list(rows[0].keys()) if rows else [])
    if not cols:
        return str(rows)

    # Cabeçalho Markdown
    header = "| " + " | ".join(cols) + " |"
    separator = "| " + " | ".join("---" for _ in cols) + " |"
    lines = [header, separator]

    for row in rows[:200]:  # limitar rendição visual
        cells = [str(row.get(c, "")) for c in cols]
        lines.append("| " + " | ".join(cells) + " |")

    extra = len(rows) - 200
    if extra > 0:
        lines.append(f"\n_... e mais {extra} registro(s) não exibido(s)._")

    return "\n".join(lines)
