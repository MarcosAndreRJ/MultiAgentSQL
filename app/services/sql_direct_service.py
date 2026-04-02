"""
SQL Direct Service: Detecta e executa comandos SQL enviados diretamente pelo usuário.
Permite bypass da LLM para comandos explícitos, garantindo performance e controle.
"""
import re
from typing import Optional

from app.core.logger import get_logger
from app.core import agent_registry
from app.schemas.chat import ChatResponse, Session
from app.schemas.execution import DBExecuteRequest
from app.services.alias_service import resolve_message_aliases
from app.services import progress_service
from app.tools import db_execute
from app.utils.text_formatter import format_rows

logger = get_logger("sql_direct_service")

# Padrões que indicam SQL direto (case-insensitive)
_SQL_START_PATTERNS = [
    r"^\s*SELECT\b",
    r"^\s*SHOW\b",
    r"^\s*DESCRIBE\b",
    r"^\s*EXPLAIN\b",
    r"^\s*WITH\b",
    r"^\s*UPDATE\b",
    r"^\s*INSERT\b",
    r"^\s*DELETE\b",
    r"^\s*CREATE\b",
    r"^\s*ALTER\b",
    r"^\s*DROP\b",
    r"^\s*EXECSQL[:\s]", # Fixo solicitado pelo usuário
]

def is_sql_direct(message: str) -> bool:
    """Verifica se a mensagem é um comando SQL direto."""
    msg_upper = message.strip().upper()
    for pattern in _SQL_START_PATTERNS:
        if re.match(pattern, msg_upper):
            return True
    return False

async def execute_direct(
    agent_id: str,
    message: str,
    session: Session,
    run_id: str
) -> Optional[ChatResponse]:
    """
    Detecta, resolve e executa SQL direto.
    Retorna ChatResponse se for SQL direto, senão None para seguir o pipeline normal.
    """
    if not is_sql_direct(message):
        return None

    logger.info(f"[DIRECT_SQL_DETECTED] agent={agent_id} | session={session.session_id}")
    await progress_service.emit_step(session.session_id, run_id, "sql_direct", status="active")

    # 1. Limpar prefixo 'execsql:' se existir
    raw_sql = message.strip()
    if raw_sql.lower().startswith("execsql:"):
        raw_sql = raw_sql[8:].strip()
    elif raw_sql.lower().startswith("execsql "):
        raw_sql = raw_sql[7:].strip()

    # 2. Resolver Aliases dentro do SQL
    # Ex: SELECT * FROM @Projeto -> SELECT * FROM Projeto
    resolved_sql, alias_hits = resolve_message_aliases(agent_id, raw_sql)
    if alias_hits:
        logger.info(f"[DIRECT_SQL_ALIAS_RESOLVED] Resolvidos {len(alias_hits)} aliases no SQL")

    # 3. Identificar Agente e Configuração de Banco
    config = agent_registry.get(agent_id)
    if not config or not config.database:
        error_msg = "[ERRO]\nAgente não possui base de dados configurada para execução direta."
        await progress_service.emit_step(session.session_id, run_id, "sql_direct", status="failed")
        return ChatResponse(
            session_id=session.session_id,
            agent_id=agent_id,
            response=error_msg,
            status="error"
        )

    # 4. Classificar e Validar SQL (leitura vs escrita) via db_execute/guard_engine
    # O db_execute.execute já chama o guard_engine internamente se configurado.
    is_write = not resolved_sql.strip().upper().startswith(("SELECT", "SHOW", "DESCRIBE", "EXPLAIN", "WITH"))
    mode = "write" if is_write else "read"
    
    req = DBExecuteRequest(sql=resolved_sql, mode=mode)
    
    try:
        # 5. Executar
        result = db_execute.execute(req, config)
        
        if result.success:
            logger.info(f"[DIRECT_SQL_EXECUTED] Sucesso | rows={getattr(result, 'rows_affected', 0)}")
            
            # Formatar Resposta (seguindo o padrão solicitado)
            response_text = (
                "[RESUMO]\n"
                "Executei o SQL informado diretamente.\n\n"
                f"[SQL]\n```sql\n{resolved_sql}\n```\n\n"
            )
            
            # Adicionar bloco de RESULTADO se for uma consulta de leitura
            if not is_write:
                if result.rows and len(result.rows) > 0:
                    formatted_table = format_rows(result.rows, result.columns, max_rows=50)
                    response_text += f"[RESULTADO]\n{formatted_table}\n\n"
                    response_text += f"[STATUS]\nExecutado com sucesso\nRegistros retornados: {len(result.rows)}"
                else:
                    response_text += "[RESULTADO]\n(nenhum registro encontrado)\n\n"
                    response_text += "[STATUS]\nExecutado com sucesso\nRegistros retornados: 0"
            else:
                response_text += f"[STATUS]\nExecutado com sucesso\nLinhas afetadas: {result.rows_affected}"

            await progress_service.emit_step(session.session_id, run_id, "sql_direct", status="completed")
            
            return ChatResponse(
                session_id=session.session_id,
                agent_id=agent_id,
                response=response_text,
                sql_executed=resolved_sql,
                execution_result=result.model_dump(),
                status="completed"
            )
        else:
            # Caso de erro (ex: sintaxe ou guard block)
            logger.warning(f"[DIRECT_SQL_FAILED] Erro: {result.error}")
            
            response_text = (
                "[RESUMO]\n"
                "Falha na execução direta do SQL.\n\n"
                f"[SQL]\n```sql\n{resolved_sql}\n```\n\n"
                f"[ERRO]\n{result.error}\n\n"
                f"[STATUS]\nFalhou na execução"
            )
            
            await progress_service.emit_step(session.session_id, run_id, "sql_direct", status="failed")

            return ChatResponse(
                session_id=session.session_id,
                agent_id=agent_id,
                response=response_text,
                status="error"
            )

    except Exception as e:
        logger.error(f"[DIRECT_SQL_EXCEPTION] {str(e)}")
        await progress_service.emit_step(session.session_id, run_id, "sql_direct", status="failed")
        return ChatResponse(
            session_id=session.session_id,
            agent_id=agent_id,
            response=f"[ERRO]\nOcorreu um erro interno: {str(e)}",
            status="error"
        )
