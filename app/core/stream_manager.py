import asyncio
from typing import AsyncGenerator
from app.core.logger import get_logger

logger = get_logger("stream_manager")

# {session_id: [queues]}
_session_queues: dict[str, list[asyncio.Queue]] = {}

def get_queue(session_id: str) -> asyncio.Queue:
    """Cria e registra uma nova fila para uma sessão."""
    queue = asyncio.Queue()
    if session_id not in _session_queues:
        _session_queues[session_id] = []
    _session_queues[session_id].append(queue)
    return queue

def remove_queue(session_id: str, queue: asyncio.Queue):
    """Remove uma fila de uma sessão."""
    if session_id in _session_queues:
        if queue in _session_queues[session_id]:
            _session_queues[session_id].remove(queue)
        if not _session_queues[session_id]:
            del _session_queues[session_id]

async def broadcast_event(session_id: str, event_data: dict):
    """Envia um evento para todas as filas conectadas à sessão."""
    if session_id in _session_queues:
        for queue in _session_queues[session_id]:
            await queue.put(event_data)
