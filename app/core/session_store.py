"""
Session Store: gerencia memória de conversas por agente.
Armazenamento em memória (runtime), isolado por agente + sessão.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.core.logger import get_logger
from app.core.settings import settings
from app.schemas.chat import Session, HistoryMessage

logger = get_logger("session_store")

# {session_id: Session}
_sessions: dict[str, Session] = {}


def get_or_create(agent_id: str, session_id: Optional[str] = None, channel: str = "web") -> Session:
    """
    Obtém sessão existente ou cria uma nova.
    
    Args:
        agent_id: ID do agente.
        session_id: ID da sessão (se None, cria nova).
        channel: Canal de origem ("web" | "telegram" | "cli").
    """
    if session_id and session_id in _sessions:
        session = _sessions[session_id]
        # Verificar se a sessão pertence ao agente correto
        if session.agent_id != agent_id:
            logger.warning(f"Sessão {session_id} pertence ao agente {session.agent_id}, não {agent_id}")
            return _create_session(agent_id, channel)
        return session

    return _create_session(agent_id, channel, session_id)


def _create_session(agent_id: str, channel: str, session_id: Optional[str] = None) -> Session:
    """Cria uma nova sessão."""
    sid = session_id or f"sess_{uuid.uuid4().hex[:16]}"
    session = Session(
        session_id=sid,
        agent_id=agent_id,
        channel=channel,
    )
    _sessions[sid] = session
    logger.debug(f"Nova sessão criada: {sid} | agente={agent_id}")
    return session


def get(session_id: str) -> Optional[Session]:
    """Busca sessão por ID."""
    return _sessions.get(session_id)


def add_message(
    session_id: str, 
    role: str, 
    content: str, 
    metadata: Optional[dict] = None,
    msg_id: Optional[str] = None,
    msg_type: str = "message"
) -> str:
    """Adiciona mensagem ao histórico da sessão."""
    session = _sessions.get(session_id)
    if not session:
        return ""

    mid = msg_id or (f"evt_{uuid.uuid4().hex[:8]}" if msg_type == "event" else f"msg_{uuid.uuid4().hex[:8]}")
    
    msg = HistoryMessage(
        id=mid,
        role=role,
        content=content,
        type=msg_type,
        metadata=metadata or {},
    )
    session.history.append(msg)

    # Limitar histórico ao máximo configurado
    max_msgs = settings.SESSION_MAX_MESSAGES
    if len(session.history) > max_msgs:
        # Preservar mensagens mais recentes
        session.history = session.history[-max_msgs:]

    session.updated_at = datetime.now(timezone.utc)
    return mid


def update_history_item(session_id: str, item_id: str, status: Optional[str] = None, metadata: Optional[dict] = None) -> bool:
    """Atualiza metadados de um item (mensagem ou evento) no histórico."""
    session = _sessions.get(session_id)
    if not session:
        return False

    for msg in session.history:
        if msg.id == item_id:
            if status:
                msg.metadata["status"] = status
                if status == "completed":
                    msg.metadata["completed_at"] = datetime.now(timezone.utc).isoformat()
            if metadata:
                msg.metadata.update(metadata)
            
            session.updated_at = datetime.now(timezone.utc)
            return True
    
    return False


def get_history_item(session_id: str, item_id: str) -> Optional[HistoryMessage]:
    """Busca um item específico no histórico."""
    session = _sessions.get(session_id)
    if not session:
        return None
    for msg in session.history:
        if msg.id == item_id:
            return msg
    return None


def update_context(
    session_id: str,
    current_goal: Optional[str] = None,
    last_sql_generated: Optional[str] = None,
    last_sql_executed: Optional[str] = None,
    recent_tables: Optional[list[str]] = None,
    recent_views: Optional[list[str]] = None,
    recent_triggers: Optional[list[str]] = None,
    last_change: Optional[dict] = None,
) -> None:
    """Atualiza o contexto operacional da sessão."""
    session = _sessions.get(session_id)
    if not session:
        return

    if current_goal is not None:
        session.current_goal = current_goal

    if last_sql_generated is not None:
        session.last_sql_generated = last_sql_generated

    if last_sql_executed is not None:
        session.last_sql_executed = last_sql_executed

    if recent_tables is not None:
        # Adicionar sem duplicatas, manter os mais recentes no topo
        existing = session.recent_objects.get("tables", [])
        combined = recent_tables + [t for t in existing if t not in recent_tables]
        session.recent_objects["tables"] = combined[:10]

    if recent_views is not None:
        existing = session.recent_objects.get("views", [])
        combined = recent_views + [v for v in existing if v not in recent_views]
        session.recent_objects["views"] = combined[:10]

    if recent_triggers is not None:
        existing = session.recent_objects.get("triggers", [])
        combined = recent_triggers + [t for t in existing if t not in recent_triggers]
        session.recent_objects["triggers"] = combined[:10]

    if last_change is not None:
        session.last_changes.insert(0, last_change)
        session.last_changes = session.last_changes[:10]

    session.updated_at = datetime.now(timezone.utc)


def add_pending_action(session_id: str, action_summary: dict) -> None:
    """Registra uma pending action na sessão."""
    session = _sessions.get(session_id)
    if not session:
        return
    session.pending_actions.append(action_summary)
    session.updated_at = datetime.now(timezone.utc)


def remove_pending_action(session_id: str, action_id: str) -> None:
    """Remove uma pending action da sessão (confirmada ou cancelada)."""
    session = _sessions.get(session_id)
    if not session:
        return
    session.pending_actions = [
        a for a in session.pending_actions if a.get("id") != action_id
    ]
    session.updated_at = datetime.now(timezone.utc)


def reset(session_id: str) -> None:
    """Limpa o contexto de uma sessão mantendo-a ativa."""
    session = _sessions.get(session_id)
    if not session:
        return
    session.history = []
    session.current_goal = None
    session.last_sql_generated = None
    session.last_sql_executed = None
    session.recent_objects = {"tables": [], "views": [], "triggers": []}
    session.pending_actions = []
    session.last_changes = []
    session.updated_at = datetime.now(timezone.utc)
    logger.info(f"Sessão resetada: {session_id}")


def get_recent_history(session_id: str, max_messages: int = 10) -> list[HistoryMessage]:
    """Retorna o histórico recente da sessão."""
    session = _sessions.get(session_id)
    if not session:
        return []
    return session.history[-max_messages:]


def list_all() -> list[Session]:
    """Lista todas as sessões ativas."""
    return list(_sessions.values())
