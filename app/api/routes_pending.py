"""
API Routes: Pending Actions
GET /api/pending - listar pending actions
GET /api/pending/{action_id} - detalhar pending action
POST /api/pending/{action_id}/confirm - confirmar
POST /api/pending/{action_id}/cancel - cancelar
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.pending_service import list_pending, get_pending
from app.core import pending_actions as pa_store

router = APIRouter(prefix="/api/pending", tags=["pending"])


class PendingActionRequest(BaseModel):
    agent_id: str
    session_id: str


@router.get("/")
async def list_pending_actions(agent_id: Optional[str] = None, session_id: Optional[str] = None):
    """Lista pending actions com filtros opcionais."""
    return list_pending(agent_id=agent_id, session_id=session_id)


@router.get("/{action_id}")
async def get_pending_action(action_id: str):
    """Detalhes de uma pending action."""
    action = get_pending(action_id)
    if not action:
        raise HTTPException(status_code=404, detail=f"Pending action '{action_id}' não encontrada")
    return action


@router.post("/{action_id}/confirm")
async def confirm_action(action_id: str, req: PendingActionRequest):
    """Confirma uma pending action — NÃO executa, apenas confirma. Use o chat para executar."""
    from app.services.chat_service import process_message
    from app.schemas.chat import ChatMessage
    
    # Usar o chat_service para processar a confirmação (mantém o fluxo correto)
    msg = ChatMessage(
        agent_id=req.agent_id,
        session_id=req.session_id,
        message=f"confirmar {action_id}",
    )
    return await process_message(msg)


@router.post("/{action_id}/cancel")
async def cancel_action(action_id: str, req: PendingActionRequest):
    """Cancela uma pending action."""
    success, reason = pa_store.cancel(action_id, req.agent_id, req.session_id)
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "action_id": action_id, "message": reason}
