"""
API Routes: Health
GET /api/health/providers - saúde dos providers
GET /api/health/database - saúde do MySQL
GET /api/health/runtime - informações de execução
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.dashboard import health_service

router = APIRouter(prefix="/api/health", tags=["dashboard", "health"])

@router.get("/database")
async def db_health(db: Session = Depends(get_db)):
    """Verifica e reporta se o MySQL está operacional."""
    return await health_service.check_database_health(db)

@router.get("/providers")
async def providers_health(db: Session = Depends(get_db)):
    """
    Verifica e reporta se cada provider configurado está vivo.
    Ollama local, Gemini, etc.
    """
    return await health_service.check_providers_health(db)

@router.get("/runtime")
async def runtime_health():
    """Reporta uptime, consumo de memória e versão do sistema."""
    return await health_service.get_runtime_health()
