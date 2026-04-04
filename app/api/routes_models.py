from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.model import ModelRead, ProviderCatalogRead
from app.services.dashboard import models_service

router = APIRouter(prefix="/api/models", tags=["Models"])


@router.get("/", response_model=List[ModelRead])
async def list_models(
    provider_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Lista todos os modelos cadastrados.
    Opcionalmente filtra por provider_id.
    """
    return await models_service.get_all_models(db, provider_id)


@router.get("/catalog", response_model=List[ProviderCatalogRead])
async def get_catalog(db: Session = Depends(get_db)):
    """
    Retorna o catálogo de modelos agrupado por provider.
    Ideal para a tela de Models da plataforma.
    """
    return await models_service.get_models_catalog(db)


@router.post("/sync/{provider_id}")
async def sync_models(provider_id: int, db: Session = Depends(get_db)):
    """
    Força a sincronização de modelos de um provider específico.
    """
    await models_service.sync_provider_models(db, provider_id)
    return {"status": "success", "message": f"Modelos do provider {provider_id} sincronizados."}
