"""
Chat Service: orquestra o processamento de mensagens dos agentes.
Ponto central que recebe mensagem, identifica agente, obtém sessão e delega.
"""
import asyncio
from typing import Optional

from app.agents.base_agent import BaseAgent
from app.agents.database_agent import DatabaseAgent
from app.agents.principal_agent import PrincipalAgent
from app.core import session_store, agent_registry
from app.core.logger import get_logger
from app.core.pending_actions import confirm, get as get_pa, mark_executed
from app.schemas.chat import ChatMessage, ChatResponse, Session
from app.schemas.execution import DBExecuteRequest
from app.services import progress_service, fastpath_service, fastpath_v2_service
from app.services import sql_direct_service, nl_sql_fastpath_service
from app.services.observability.execution_observability_service import generate_execution_id
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.services.platform import agent_governance_service

logger = get_logger("chat_service")

# Cache de instâncias de agentes: {agent_id: BaseAgent}
_agent_instances: dict[str, BaseAgent] = {}

# Tarefas ativas por session_id: {session_id: asyncio.Task}
_active_tasks: dict[str, asyncio.Task] = {}


def get_agent_instance(agent_id: str, db: Optional[Session] = None) -> Optional[BaseAgent]:
    """
    Obtém instância do agente, criando se necessário.
    Utiliza o resolve_agent_runtime_config para garantir governança.
    """
    if agent_id in _agent_instances:
        return _agent_instances[agent_id]

    # Resolve a configuração efetiva (DB > YAML)
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True
    
    try:
        runtime_config = agent_governance_service.resolve_agent_runtime_config(db, agent_id)
        
        if not runtime_config.is_active:
            logger.warning(f"Tentativa de acesso a agente inativo: {agent_id}")
            return None

        # Resolve a configuração completa (Pydantic AgentConfig) a partir do banco de dados (Platform DB)
        # Fonte absoluta: Governança centralizada
        config = agent_governance_service.resolve_full_agent(db, agent_id)
        if not config:
            logger.error(f"Falha crítica: Configuração do agente '{agent_id}' não encontrada no banco.")
            return None

        if config.type == "principal":
            instance = PrincipalAgent(config)
        elif config.type == "mysql-specialist":
            instance = DatabaseAgent(config)
        else:
            logger.error(f"Tipo de agente desconhecido: {config.type}")
            return None

        _agent_instances[agent_id] = instance
        logger.debug(f"Instância de agente criada: {agent_id} (tipo={config.type} | source={runtime_config.source})")
        return instance

    except Exception as e:
        logger.error(f"Erro ao resolver/criar agente '{agent_id}': {e}")
        return None
    finally:
        if own_session:
            db.close()


async def process_message(msg: ChatMessage, db: Optional[Session] = None) -> ChatResponse:
    """
    Processa uma mensagem de chat completa.
    
    Fluxo:
    1. Validar agente
    2. Obter/criar sessão
    3. Verificar se é confirmação/cancelamento de pending action
    4. Delegar ao agente adequado
    """
    logger.info(f"[CHAT] agent={msg.agent_id} | session={msg.session_id} | msg='{msg.message[:80]}'")

    # Gerar Correlation ID para observabilidade
    execution_id = generate_execution_id()
    logger.info(f"[OBSERVABILITY] correlation_id={execution_id}")

    # 1. Validar agente e status de ativação (Governança)
    agent = get_agent_instance(msg.agent_id, db=db)
    if not agent:
        logger.error(f"Agente não encontrado: {msg.agent_id}")
        return ChatResponse(
            session_id=msg.session_id,
            agent_id=msg.agent_id,
            response=f"[ERRO]\nAgente '{msg.agent_id}' não encontrado.",
            status="error",
        )

    # 2. Obter/criar sessão
    session = session_store.get_or_create(msg.agent_id, msg.session_id)

    # Injetar anexos no contexto da mensagem
    if getattr(msg, "attached_files", None):
        from app.services.file_service import process_attachments
        anexos_texto = process_attachments(msg.session_id, msg.attached_files)
        if anexos_texto:
            logger.info(f"Anexando conteúdo de {len(msg.attached_files)} arquivo(s) à mensagem")
            msg.message += f"\n\n{anexos_texto}"

    # 3. Resolver aliases @Tabela → nome real (antes de qualquer processamento)
    resolved_message, alias_hits = _resolve_aliases(msg.agent_id, msg.message)
    if alias_hits:
        logger.info(f"[ALIASES] Resolvidos {len(alias_hits)} alias(es): {alias_hits}")
    resolved_tables = list(alias_hits.values()) if alias_hits else []

    # 4. Verificar se é comando especial (confirmar/cancelar pending action)
    effective_msg = msg.model_copy(update={"message": resolved_message})
    special_response = await _handle_special_commands(effective_msg, session, agent)
    if special_response:
        return special_response

    # 5. Processar via agente (com mensagem com aliases resolvidos)
    logger.info(f"Delegando ao agente | id={msg.agent_id} | type={agent.agent_type}")
    
    # Iniciar ciclo de execução (run_id) para eventos persistentes
    run_id = await progress_service.start_run(msg.session_id)
    
    # --- CAMINHO RÁPIDO: SQL DIRETO ---
    direct_sql_response = await sql_direct_service.execute_direct(msg.agent_id, msg.message, session, run_id)
    if direct_sql_response:
        await progress_service.complete_run(msg.session_id, run_id)
        return direct_sql_response

    # --- CAMINHO RÁPIDO: TRADUÇÃO DETERMINÍSTICA NL-SQL ---
    nl_fastpath_response = await nl_sql_fastpath_service.translate_and_execute(msg.agent_id, msg.message, session, run_id)
    if nl_fastpath_response:
        await progress_service.complete_run(msg.session_id, run_id)
        return nl_fastpath_response

    await progress_service.emit_step(msg.session_id, run_id, "parsing", status="completed")
    
    # Registrar task atual para permitir cancelamento
    current_task = asyncio.current_task()
    _active_tasks[msg.session_id] = current_task
    
    try:
        response = await agent.process(
            resolved_message, 
            session, 
            resolved_tables=resolved_tables, 
            run_id=run_id,
            execution_id=execution_id,
            db=db
        )
        # Marcar todos os eventos da run como concluídos ao terminar
        await progress_service.complete_run(msg.session_id, run_id)
        return response
    except asyncio.CancelledError:
        logger.warning(f"[CHAT] Mensagem cancelada pelo usuário: session={msg.session_id}")
        return ChatResponse(
            session_id=msg.session_id,
            agent_id=msg.agent_id,
            response="[INTERROMPIDO]\nA geração foi cancelada pelo usuário.",
            status="error",
        )
    finally:
        # Limpar task ao finalizar (sucesso ou erro)
        if _active_tasks.get(msg.session_id) == current_task:
            _active_tasks.pop(msg.session_id, None)


async def cancel_message(session_id: str):
    """Interrompe uma tarefa em andamento para a sessão especificada."""
    task = _active_tasks.get(session_id)
    if task:
        logger.info(f"[CHAT] Solicitando cancelamento da task: session={session_id}")
        task.cancel()
        return True
    return False


async def _handle_special_commands(
    msg: ChatMessage,
    session: Session,
    agent: BaseAgent,
) -> Optional[ChatResponse]:
    """
    Detecta e processa comandos especiais:
    - /confirmar <id> ou confirmar <id>
    - /cancelar <id> ou cancelar <id>
    - /reset
    """
    text = msg.message.strip().lower()

    # Confirmar pending action
    if text.startswith(("confirmar ", "/confirmar ", "confirm ")):
        action_id = text.split(" ", 1)[-1].strip()
        return await _confirm_pending(action_id, msg, session, agent)

    # Cancelar pending action
    if text.startswith(("cancelar ", "/cancelar ", "cancel ")):
        action_id = text.split(" ", 1)[-1].strip()
        return await _cancel_pending(action_id, msg, session, agent)

    # Reset de sessão
    if text in ("/reset", "reset sessão", "reset session"):
        session_store.reset(session.session_id)
        return ChatResponse(
            session_id=session.session_id,
            agent_id=msg.agent_id,
            response="[STATUS]\nSessão resetada com sucesso.",
            status="completed",
        )

    return None


async def _confirm_pending(
    action_id: str,
    msg: ChatMessage,
    session: Session,
    agent: BaseAgent,
) -> ChatResponse:
    """Confirma e executa uma pending action."""
    from app.core import pending_actions as pa_store

    success, reason, action = pa_store.confirm(action_id, msg.agent_id, session.session_id)

    if not success:
        return ChatResponse(
            session_id=session.session_id,
            agent_id=msg.agent_id,
            response=f"[ERRO]\n{reason}",
            status="error",
        )

    # Executar o SQL confirmado
    config = agent_registry.get(msg.agent_id)
    if not config or not config.database:
        return ChatResponse(
            session_id=session.session_id,
            agent_id=msg.agent_id,
            response="[ERRO]\nAgente não possui banco de dados configurado.",
            status="error",
        )

    req = DBExecuteRequest(sql=action.sql, mode="write")
    result = db_execute.execute(req, config)

    # Marcar como executado
    pa_store.mark_executed(action_id, result.model_dump())
    session_store.remove_pending_action(session.session_id, action_id)

    if result.success:
        session_store.update_context(session.session_id, last_sql_executed=action.sql)
        response_text = (
            f"[RESUMO]\n{action.summary}\n\n"
            f"[SQL]\n```sql\n{action.sql}\n```\n\n"
            f"[STATUS]\nExecutado com sucesso\n"
            f"Linhas afetadas: {result.rows_affected} ({result.execution_time_ms:.1f}ms)"
        )
    else:
        response_text = (
            f"[RESUMO]\n{action.summary}\n\n"
            f"[SQL]\n```sql\n{action.sql}\n```\n\n"
            f"[ERRO]\n{result.error}\n\n"
            f"[STATUS]\nFalhou na execução"
        )

    session_store.add_message(session.session_id, "assistant", response_text)
    return ChatResponse(
        session_id=session.session_id,
        agent_id=msg.agent_id,
        response=response_text,
        sql_executed=action.sql if result.success else None,
        execution_result=result.model_dump() if result.success else None,
        status="completed" if result.success else "error",
    )


async def _cancel_pending(
    action_id: str,
    msg: ChatMessage,
    session: Session,
    agent: BaseAgent,
) -> ChatResponse:
    """Cancela uma pending action."""
    from app.core import pending_actions as pa_store

    success, reason = pa_store.cancel(action_id, msg.agent_id, session.session_id)
    session_store.remove_pending_action(session.session_id, action_id)

    response_text = (
        f"[STATUS]\nPending action {action_id}: {reason}"
        if success
        else f"[ERRO]\n{reason}"
    )

    session_store.add_message(session.session_id, "assistant", response_text)
    return ChatResponse(
        session_id=session.session_id,
        agent_id=msg.agent_id,
        response=response_text,
        status="completed" if success else "error",
    )


def reload_agents() -> None:
    """Recarrega todos os agentes (limpa cache de instâncias)."""
    global _agent_instances
    _agent_instances = {}
    agent_registry.reload_agents()
    logger.info("Agentes recarregados")


def _resolve_aliases(agent_id: str, message: str) -> tuple[str, dict[str, str]]:
    """
    Resolve aliases @Token na mensagem usando o AliasService.
    Retorna (mensagem_resolvida, mapeamento_hits).
    Silencioso se não houver aliases configurados.
    """
    try:
        from app.services.alias_service import resolve_message_aliases
        return resolve_message_aliases(agent_id, message)
    except Exception as e:
        logger.warning(f"[ALIASES] Erro ao resolver aliases para '{agent_id}': {e}")
        return message, {}

