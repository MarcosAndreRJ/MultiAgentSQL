"""
API Routes: DB Digest
POST /api/digest/generate?agent_id=... — gera/regenera digest
GET  /api/digest?agent_id=...           — retorna digest completo
GET  /api/digest/status?agent_id=...    — retorna status do digest
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.core import agent_registry
from app.core.logger import get_logger
from app.schemas.digest import DBDigest, DigestStatus
from app.services import digest_service
from app.db.session import get_db

logger = get_logger("routes_digest")

router = APIRouter(prefix="/api/digest", tags=["digest"])


def _get_agent_config(agent_id: str):
    config = agent_registry.get(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Agente '{agent_id}' não encontrado")
    if not config.database:
        raise HTTPException(
            status_code=400,
            detail=f"Agente '{agent_id}' não possui banco de dados configurado",
        )
    return config


@router.post("/generate")
async def generate_digest(
    agent_id: str = Query(..., description="ID do agente"),
    db: Session = Depends(get_db),
) -> DBDigest:
    """Gera ou regenera o digest do banco vinculado ao agente."""
    config = _get_agent_config(agent_id)
    try:
        digest = digest_service.generate_digest(config, db=db)
        # Gerar/atualizar aliases automaticamente após o digest
        from app.services.alias_service import generate_aliases_from_digest
        generate_aliases_from_digest(digest)
        return digest
    except Exception as e:
        logger.error(f"[DIGEST] Erro ao gerar digest para '{agent_id}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_digest_status(
    agent_id: str = Query(..., description="ID do agente"),
    db: Session = Depends(get_db),
) -> DigestStatus:
    """Retorna status do digest (existe? quando foi gerado? quantas tabelas?)."""
    # Valida que o agente existe
    config = agent_registry.get(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Agente '{agent_id}' não encontrado")
    return digest_service.get_digest_status(agent_id, db=db)


@router.get("/")
async def get_digest(
    agent_id: str = Query(..., description="ID do agente"),
    db: Session = Depends(get_db),
) -> DBDigest:
    """Retorna o digest completo salvo para o agente."""
    config = agent_registry.get(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Agente '{agent_id}' não encontrado")
    
    digest = digest_service.load_digest(agent_id, db=db)
    if not digest:
        raise HTTPException(
            status_code=404,
            detail=f"Digest não encontrado para o agente '{agent_id}'. Execute POST /api/digest/generate primeiro.",
        )
    return digest


@router.get("/get")
async def get_digest_alias(
    agent_id: str = Query(..., description="ID do agente"),
    db: Session = Depends(get_db),
) -> DBDigest:
    """Alias de /api/digest/ para compatibilidade com o frontend."""
    return await get_digest(agent_id=agent_id, db=db)
