"""
API Routes: Models
GET /api/models - listar todos os modelos de todas as fontes
GET /api/providers/{id}/models - listar modelos de um provider específico
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.dashboard import models_service

router = APIRouter(tags=["dashboard", "models"])

@router.get("/api/models")
async def list_models(db: Session = Depends(get_db)):
    """Lista todos os modelos de LLM cadastrados no banco."""
    models = await models_service.get_all_models(db)
    return {"models": models}

@router.get("/api/providers/{provider_id}/models")
async def list_models_by_provider(provider_id: int, db: Session = Depends(get_db)):
    """Lista modelos vinculados a um provider específico."""
    models = await models_service.get_all_models(db, provider_id)
    return {"models": models}
