"""
API Routes: Chat
POST /api/chat - enviar mensagem para agente
GET /api/chat/{session_id}/history - histÃ³rico da sessÃ£o
DELETE /api/chat/{session_id} - resetar sessÃ£o
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core import session_store, stream_manager
from app.schemas.chat import ChatMessage
from app.services.chat_service import process_message, cancel_message

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/")
async def send_message(msg: ChatMessage, db: Session = Depends(get_db)):
    """Envia mensagem para um agente e recebe resposta."""
    if not msg.message.strip():
        raise HTTPException(status_code=400, detail="Mensagem nÃ£o pode estar vazia")
    
    # Criar session_id se nÃ£o fornecido
    # Compat legado: frontend antigo envia conversation_id em vez de session_id
    if not msg.session_id and msg.conversation_id:
        msg.session_id = msg.conversation_id

    if not msg.session_id:
        import uuid
        msg.session_id = f"sess_{uuid.uuid4().hex[:16]}"
    
    return await process_message(msg, db=db)


@router.get("/history/{session_id}/{agent_id}")
async def get_history(session_id: str, agent_id: str):
    """
    Retorna histÃ³rico de mensagens da sessÃ£o filtrado por agente.
    Formato compatÃ­vel com o frontend: { ok: true, messages: [...] }
    """
    session = session_store.get(session_id)
    
    # Se a sessÃ£o nÃ£o existir, retorna lista vazia (UX amigÃ¡vel para chat novo)
    if not session:
        return {
            "ok": True,
            "session_id": session_id,
            "agent_id": agent_id,
            "messages": [],
            "pending_actions": [],
        }
    
    # Mapear histÃ³rico para formato esperado (createdAt em vez de timestamp)
    messages = []
    for m in session.history:
        messages.append({
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "type": m.type,
            "metadata": m.metadata,
            "createdAt": m.timestamp.isoformat() if m.timestamp else None
        })

    return {
        "ok": True,
        "session_id": session_id,
        "agent_id": session.agent_id,
        "messages": messages,
        "pending_actions": session.pending_actions,
        "current_goal": session.current_goal,
    }


@router.delete("/{session_id}")
async def reset_session(session_id: str):
    """Reseta o contexto de uma sessÃ£o."""
    session_store.reset(session_id)
    return {"status": "ok", "session_id": session_id}


@router.post("/stop")
async def stop_chat(session_id: str):
    """Interrompe a geraÃ§Ã£o atual para a sessÃ£o."""
    cancelled = await cancel_message(session_id)
    return {"status": "cancelled" if cancelled else "not_found", "session_id": session_id}


@router.get("/events/{session_id}")
async def event_stream(session_id: str, request: Request):
    """Stream SSE de eventos de progresso para uma sessÃ£o."""
    async def event_generator():
        queue = stream_manager.get_queue(session_id)
        try:
            while True:
                # Verificar se o cliente ainda estÃ¡ conectado
                if await request.is_disconnected():
                    break
                
                try:
                    # Timeout curto para verificar desconexÃ£o periodicamente
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield f"event: message\ndata: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    continue
        finally:
            stream_manager.remove_queue(session_id, queue)

    import asyncio
    import json
    return StreamingResponse(event_generator(), media_type="text/event-stream")

