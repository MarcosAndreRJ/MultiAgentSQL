"""
NL SQL FastPath Service: Traduz pedidos simples em linguagem natural para SQL de forma determinística.
Usa regex, filter_parser e join_resolver para garantir alta confiança sem LLM.
"""
import re
from typing import Optional, List

from app.core.logger import get_logger
from app.core import agent_registry
from app.schemas.chat import ChatResponse, Session
from app.services import progress_service, filter_parser, join_resolver, query_builder
from app.services.alias_service import resolve_message_aliases, load_aliases
from app.services.digest_service import load_digest
from app.tools import db_execute
from app.schemas.execution import DBExecuteRequest
from app.utils.text_formatter import format_rows

logger = get_logger("nl_sql_fastpath")

# Regex para detectar o padrão: "Liste [campos] de [tabelas] [filtros]"
# Opções de verbos: Liste, Mostrar, Traga, Selecione, Query, etc.
_LIST_PATTERN = re.compile(
    r"^\s*(?:liste|mostre|traga|selecione|exiba|mostrar|listar|quero\s+ver)\b"  
    r"(?:\s+(?:todas?|todos?|as|os))?\s*"                                     
    r"(?P<fields>.*?)\s*"                                                      # Campos (opcional)
    r"(?:de\s+|from\s+|das?\s+|dos?\s+)"                                       # Conector (de)
    r"(?P<tables>@[A-Za-z0-9_,\s@]+)"                                          # Tabelas (obrigatório @Alias)
    r"(?P<remainder>.*)$",                                                     # Opcionais (filtros, ordens)
    re.IGNORECASE | re.DOTALL
)

# Padrão simplificado para: "Liste @Tabela [filtros]" (quando não tem o 'de')
_LIST_SIMPLE_PATTERN = re.compile(
    r"^\s*(?:liste|mostre|traga|selecione|exiba|mostrar|listar|quero\s+ver)\b"
    r"(?:\s+(?:todas?|todos?|as|os))?\s+"
    r"(?P<tables>@[A-Za-z0-9_,\s@]+)"
    r"(?P<remainder>.*)$",
    re.IGNORECASE | re.DOTALL
)

async def translate_and_execute(
    agent_id: str,
    message: str,
    session: Session,
    run_id: str
) -> Optional[ChatResponse]:
    """
    Tenta traduzir a mensagem NL para SQL determinístico.
    Retorna ChatResponse se houver match de alta confiança, senão None.
    """
    match = _LIST_PATTERN.match(message)
    if not match:
        # Tenta o padrão simples se o complexo falhar
        match = _LIST_SIMPLE_PATTERN.match(message)
        if not match:
            return None
        fields_raw = "*"
    else:
        fields_raw = match.group("fields").strip() or "*"

    tables_raw = match.group("tables").strip()
    remainder = match.group("remainder").strip()

    logger.info(f"[NL_SQL_TRANSLATION_MATCH] agent={agent_id} | tables={tables_raw}")
    await progress_service.emit_step(session.session_id, run_id, "nl_sql_fastpath", status="active")

    # 1. Resolver tabelas
    # Extrai tokens @Tokens de forma única e normalizada
    table_tokens = sorted(list(set(re.findall(r"@[A-Za-z0-9_]+", tables_raw.lower()))))
    if not table_tokens:
        return _fallback(f"Nenhum alias @Tabela encontrado na lista: '{tables_raw}'")

    # Busca nomes reais no AliasService
    _, table_hits = resolve_message_aliases(agent_id, tables_raw)
    
    # Normaliza chaves de hits para comparação segura
    hit_tokens = sorted(list(set(t.lower() for t in table_hits.keys())))
    real_tables = [table_hits[t] for t in table_hits if t.lower() in table_tokens]
    
    # Garantir que todos os tokens desejados foram resolvidos
    missing = [t for t in table_tokens if t not in hit_tokens]
    if missing:
        return _fallback(f"Nem todos os tokens foram resolvidos: {missing}. Tokens encontrados: {table_tokens}, Resolvidos: {hit_tokens}")
    
    real_tables = sorted(list(set(real_tables))) # Deduplicar se necessário
    if not real_tables:
        return _fallback("Nenhuma tabela válida foi extraída após resolução de aliases.")

    # 2. Carregar Digest
    digest = load_digest(agent_id)
    if not digest:
        return _fallback("Digest não encontrado para o agente.")

    # 3. Resolver JOINs se houver múltiplas tabelas
    jp = None
    if len(real_tables) == 2:
        jp = join_resolver.resolve_join(digest, real_tables[0], real_tables[1])
        if not jp:
            return _fallback(f"Não foi possível resolver JOIN automático entre {real_tables[0]} e {real_tables[1]}")
        logger.info(f"[NL_SQL_JOIN_RESOLVED] Join encontrado via FK: {jp.left_col} = {jp.right_col}")
    elif len(real_tables) > 2:
        return _fallback("Tradução determinística suporta no máximo 2 tabelas com JOIN automático.")

    # 4. Parsear Filtros, Ordem e Limite do remainder
    # Precisamos tratar o remainder para o filter_parser (que espera nomes de colunas, não @aliases)
    # Mas aqui o usuário pode ter escrito "quando @Projeto.Status = 'Ativo'"
    # Resolvemos aliases no remainder primeiro
    resolved_remainder, _ = resolve_message_aliases(agent_id, remainder)
    
    # Substituir "quando " por "onde " ou apenas remover "quando " se o parser já reconhece o resto
    if resolved_remainder.lower().startswith("quando "):
        resolved_remainder = resolved_remainder[6:].strip()
    elif " quando " in resolved_remainder.lower():
        resolved_remainder = re.sub(r"\bquando\b", " ", resolved_remainder, flags=re.IGNORECASE)

    slots = filter_parser.parse_slots(resolved_remainder)

    # 5. Extrair colunas (projeção) — busca palavras que batem com colunas do digest
    # Vamos olhar no fields_raw extraído pela regex
    all_known_cols: set[str] = set()
    for t in digest.tables:
        if t.name in real_tables:
            all_known_cols.update(c.name for c in t.columns)
    for v in digest.views:
        if v.name in real_tables:
            all_known_cols.update(c.name for c in v.columns)

    # Pegar palavras que possam ser colunas
    words = re.findall(r"\b[A-Za-z0-9_]+\b", fields_raw)
    selected_cols = [w for w in words if w.lower() in {kc.lower() for kc in all_known_cols}]
    
    # Remover duplicatas mantendo a ordem
    seen_cols = set()
    final_cols = []
    for c in selected_cols:
        canon = next((kc for kc in all_known_cols if kc.lower() == c.lower()), c)
        if canon.lower() not in seen_cols:
            final_cols.append(canon)
            seen_cols.add(canon.lower())

    # 6. Montar V2Plan para o QueryBuilder
    intent = "SELECT_JOIN" if jp else "SELECT"
    
    plan = query_builder.V2Plan(
        intent=intent,
        tables=real_tables,
        columns=final_cols,
        filters=slots.filters,
        order_by=slots.order_by,
        limit=slots.limit,
        join_path=jp,
        confidence=1.0 # Determinístico
    )

    # 6. Gerar SQL
    build_result = query_builder.build_sql(plan, digest)
    if not build_result:
        return _fallback("Falha ao construir SQL via QueryBuilder (validação de colunas provavelmente falhou).")

    # 7. Execução
    config = agent_registry.get(agent_id)
    execute_req = DBExecuteRequest(sql=build_result.sql, mode="read")
    
    try:
        result = db_execute.execute(execute_req, config)
        
        if result.success:
            response_text = (
                "[RESUMO]\n"
                "Traduzi sua solicitação para SQL e executei a consulta.\n\n"
                f"[SQL]\n```sql\n{build_result.sql}\n```\n\n"
            )
            
            # Adicionar bloco de RESULTADO se houver linhas
            if result.rows and len(result.rows) > 0:
                formatted_table = format_rows(result.rows, result.columns, max_rows=50)
                response_text += f"[RESULTADO]\n{formatted_table}\n\n"
                response_text += f"[STATUS]\nExecutado com sucesso\nRegistros retornados: {len(result.rows)}"
            else:
                response_text += "[STATUS]\nExecutado com sucesso"
            
            await progress_service.emit_step(session.session_id, run_id, "nl_sql_fastpath", status="completed")

            return ChatResponse(
                session_id=session.session_id,
                agent_id=agent_id,
                response=response_text,
                sql_executed=build_result.sql,
                execution_result=result.model_dump(),
                status="completed"
            )
        else:
            return _fallback(f"Erro na execução do SQL gerado: {result.error}")

    except Exception as e:
        logger.error(f"[NL_SQL_EXCEPTION] {str(e)}")
        return _fallback(f"Exceção interna: {str(e)}")

def _fallback(reason: str) -> Optional[ChatResponse]:
    """Loga o motivo da falha na tradução e retorna None para seguir com LLM."""
    logger.info(f"[NL_SQL_TRANSLATION_FALLBACK] Motivo: {reason}")
    # Nota: Não emitimos erro aqui, pois o pipeline deve continuar para a LLM
    return None
