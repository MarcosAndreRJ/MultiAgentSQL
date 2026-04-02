"""
Pending Service: operações sobre pending actions via API.
"""
from typing import Optional

from app.core import pending_actions as pa_store
from app.core.logger import get_logger
from app.schemas.pending import PendingAction, PendingActionList

logger = get_logger("pending_service")


def list_pending(agent_id: Optional[str] = None, session_id: Optional[str] = None) -> PendingActionList:
    """Lista pending actions com filtros opcionais."""
    if agent_id:
        actions = pa_store.list_by_agent(agent_id, session_id)
    else:
        actions = pa_store.list_all()
    
    return PendingActionList(actions=actions, total=len(actions))


def get_pending(action_id: str) -> Optional[PendingAction]:
    """Busca uma pending action pelo ID."""
    return pa_store.get(action_id)
