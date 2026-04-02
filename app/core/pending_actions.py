"""
Pending Actions: armazena e gerencia operações aguardando confirmação.
Armazenamento em memória (runtime). Não persiste entre reinicializações.
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.core.logger import get_logger
from app.core.settings import settings
from app.schemas.pending import PendingAction

logger = get_logger("pending_actions")

# Armazenamento em memória: {action_id: PendingAction}
_store: dict[str, PendingAction] = {}


def create(
    agent_id: str,
    session_id: str,
    sql: str,
    action_type: str,
    risk_level: str,
    summary: str,
    database: Optional[str] = None,
    ttl_seconds: Optional[int] = None,
) -> PendingAction:
    """
    Cria uma nova pending action e armazena em memória.
    
    Returns:
        A PendingAction criada.
    """
    action_id = f"pa_{uuid.uuid4().hex[:12]}"
    ttl = ttl_seconds or settings.PENDING_ACTION_TTL
    now = datetime.now(timezone.utc)

    action = PendingAction(
        id=action_id,
        agent_id=agent_id,
        session_id=session_id,
        database=database,
        sql=sql,
        action_type=action_type,
        risk_level=risk_level,
        summary=summary,
        created_at=now,
        expires_at=now + timedelta(seconds=ttl),
        status="pending",
    )

    _store[action_id] = action
    logger.info(f"Pending action criada: {action_id} | agente={agent_id} | tipo={action_type}")
    return action


def get(action_id: str) -> Optional[PendingAction]:
    """Busca uma pending action por ID."""
    return _store.get(action_id)


def list_by_agent(agent_id: str, session_id: Optional[str] = None) -> list[PendingAction]:
    """Lista pending actions de um agente, opcionalmente filtrado por sessão."""
    _expire_old()
    results = []
    for action in _store.values():
        if action.agent_id != agent_id:
            continue
        if session_id and action.session_id != session_id:
            continue
        results.append(action)
    return sorted(results, key=lambda a: a.created_at, reverse=True)


def list_all() -> list[PendingAction]:
    """Lista todas as pending actions."""
    _expire_old()
    return sorted(_store.values(), key=lambda a: a.created_at, reverse=True)


def confirm(action_id: str, agent_id: str, session_id: str) -> tuple[bool, str, Optional[PendingAction]]:
    """
    Confirma uma pending action para execução.
    
    Returns:
        (success, reason, action)
    """
    action = _store.get(action_id)

    if not action:
        return False, "Pending action não encontrada", None

    if action.agent_id != agent_id:
        return False, "Pending action não pertence a este agente", None

    if action.session_id != session_id:
        return False, "Pending action não pertence a esta sessão", None

    if action.status == "expired" or datetime.now(timezone.utc) > action.expires_at:
        action.status = "expired"
        return False, "Pending action expirou. Gere novamente.", None

    if action.status == "cancelled":
        return False, "Pending action já foi cancelada", None

    if action.status in ("confirmed", "executed"):
        return False, "Pending action já foi executada", None

    if action.status != "pending":
        return False, f"Status inválido: {action.status}", None

    action.status = "confirmed"
    logger.info(f"Pending action confirmada: {action_id} | agente={agent_id}")
    return True, "Confirmada com sucesso", action


def cancel(action_id: str, agent_id: str, session_id: str) -> tuple[bool, str]:
    """
    Cancela uma pending action.
    
    Returns:
        (success, reason)
    """
    action = _store.get(action_id)

    if not action:
        return False, "Pending action não encontrada"

    if action.agent_id != agent_id:
        return False, "Pending action não pertence a este agente"

    if action.session_id != session_id:
        return False, "Pending action não pertence a esta sessão"

    if action.status != "pending":
        return False, f"Não pode cancelar: status atual é '{action.status}'"

    action.status = "cancelled"
    logger.info(f"Pending action cancelada: {action_id}")
    return True, "Cancelada com sucesso"


def mark_executed(action_id: str, result: dict) -> bool:
    """Marca uma pending action como executada com resultado."""
    action = _store.get(action_id)
    if not action:
        return False
    action.status = "executed"
    action.executed_at = datetime.now(timezone.utc)
    action.execution_result = result
    return True


def _expire_old() -> None:
    """Marca como expiradas as pending actions que passaram do TTL."""
    now = datetime.now(timezone.utc)
    for action in _store.values():
        if action.status == "pending" and now > action.expires_at:
            action.status = "expired"
            logger.debug(f"Pending action expirada: {action.id}")
