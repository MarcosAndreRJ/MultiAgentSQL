"""
API Routes: Config
GET /api/config - ver configurações do app
"""
from fastapi import APIRouter
from app.services.dashboard import config_service

router = APIRouter(prefix="/api/config", tags=["dashboard", "config"])

@router.get("/")
async def get_config():
    """Retorna as configurações do sistema de forma segura (mascarada)."""
    return config_service.get_masked_config()
