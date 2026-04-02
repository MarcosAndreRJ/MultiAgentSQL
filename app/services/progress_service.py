import uuid
from datetime import datetime, timezone
from typing import Optional

from app.core import session_store, stream_manager
from app.core.logger import get_logger

logger = get_logger("progress_service")

# Mapeamento amigável de steps
STEP_LABELS = {
    "parsing": "Analisando sua pergunta...",
    "fast_path_check": "Verificando atalhos inteligentes...",
    "semantic_search": "Buscando no histórico...",
    "semantic_transform": "Adaptando consulta anterior...",
    "semantic_rank": "Escolhendo o melhor padrão...",
    "llm_call": "Consultando inteligência do modelo...",
    "sql_build": "Montando consulta SQL...",
    "guard_validation": "Validando segurança da consulta...",
    "db_execute": "Consultando banco de dados...",
    "result_format": "Organizando resultado...",
    "finalizing": "Finalizando resposta..."
}

async def start_run(session_id: str) -> str:
    """Inicia um novo ciclo de execução e retorna o run_id."""
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    logger.debug(f"Nova execução iniciada: {run_id} | session={session_id}")
    return run_id

async def emit_step(session_id: str, run_id: str, step: str, status: str = "active"):
    """
    Emite um evento de progresso, persiste no histórico e faz broadcast.
    """
    content = STEP_LABELS.get(step, f"Processando: {step}...")
    
    # Gerar ID único para este step dentro do run (ou usar o step como ID se for único por run)
    event_id = f"{run_id}_{step}"
    
    # 1. Persistir no SessionStore
    # Se já existir (status upgrade), atualizar. Se não, criar.
    existing = session_store.get_history_item(session_id, event_id)
    
    if existing:
        session_store.update_history_item(session_id, event_id, status=status)
    else:
        session_store.add_message(
            session_id=session_id,
            role="system",
            content=content,
            msg_id=event_id,
            msg_type="event",
            metadata={
                "run_id": run_id,
                "step": step,
                "status": status,
                "event_type": "progress"
            }
        )
    
    # 2. Broadcast via StreamManager (para streaming em tempo real)
    event_payload = {
        "id": event_id,
        "run_id": run_id,
        "type": "event",
        "step": step,
        "content": content,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await stream_manager.broadcast_event(session_id, event_payload)

async def complete_run(session_id: str, run_id: str):
    """
    Finaliza todos os eventos ativos de um run_id.
    """
    session = session_store.get(session_id)
    if not session:
        return

    for msg in session.history:
        if msg.type == "event" and msg.metadata.get("run_id") == run_id:
            if msg.metadata.get("status") == "active":
                await emit_step(session_id, run_id, msg.metadata.get("step"), status="completed")
