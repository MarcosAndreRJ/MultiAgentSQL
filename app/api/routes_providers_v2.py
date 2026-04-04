"""
Rotas para gerenciamento de Providers como entidade de negocio.

IMPORTANTE: este router é um rascunho v2. Não foi incluído em main.py para
evitar conflito. Se quiser ativar, podemos registrar com feature flag.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.provider import ProviderCreate, ProviderUpdate, ProviderList
from app.services.platform import provider_service
from app.utils.secrets import mask_secret
from app.core.logger import get_logger

logger = get_logger("api.routes_providers_v2")

router = APIRouter(prefix="/api/providers", tags=["providers-v2"])


@router.post("/", response_model=dict)
def api_create_provider(payload: ProviderCreate, db: Session = Depends(get_db)):
    # Debug para diagnosticar 422 e incompatibilidade de schema
    payload_debug = payload.model_dump()
    if payload_debug.get("api_key"):
        payload_debug["api_key"] = mask_secret(payload_debug["api_key"])
    
    logger.debug(f"Recebido payload para criação de Provider: {payload_debug}")
    
    try:
        created = provider_service.create_provider(db, payload)
        return {"provider": created}
    except ValueError as e:
        logger.warning(f"Erro de validação de negócio: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=ProviderList)
def api_list_providers(db: Session = Depends(get_db)):
    providers = provider_service.list_providers(db)
    return {"providers": providers}


@router.get("/{provider_id}")
def api_get_provider(provider_id: int, db: Session = Depends(get_db)):
    p = provider_service.get_provider(db, provider_id)
    if not p:
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"provider": p}


@router.put("/{provider_id}")
def api_update_provider(provider_id: int, payload: ProviderUpdate, db: Session = Depends(get_db)):
    p = provider_service.update_provider(db, provider_id, payload)
    if not p:
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"provider": p}


@router.patch("/{provider_id}/activate")
def api_activate(provider_id: int, db: Session = Depends(get_db)):
    p = provider_service.activate_provider(db, provider_id)
    if not p:
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"provider": p}


@router.patch("/{provider_id}/deactivate")
def api_deactivate(provider_id: int, db: Session = Depends(get_db)):
    p = provider_service.deactivate_provider(db, provider_id)
    if not p:
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"provider": p}


@router.post("/{provider_id}/test")
async def api_test_provider(provider_id: int, db: Session = Depends(get_db)):
    """
    Executa o teste operacional de conectividade do provider.
    """
    result = await provider_service.test_provider_connection(db, provider_id)
    if result["status"] == "error":
        if result["error"] in ["not_found"]:
            raise HTTPException(status_code=404, detail=result)
        return result
    return result


@router.post("/{provider_id}/sync-models")
async def api_sync_models(provider_id: int, db: Session = Depends(get_db)):
    """
    Sincroniza o catálogo de modelos do provider.
    """
    try:
        result = await provider_service.sync_provider_models(db, provider_id)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na sincronização: {str(e)}")


@router.get("/{provider_id}/models")
def api_get_provider_models(provider_id: int, db: Session = Depends(get_db)):
    """
    Retorna os modelos técnicos já persistidos e sincronizados para este provider.
    """
    from app.db import models as db_models
    models = db.query(db_models.LLMModel).filter(db_models.LLMModel.provider_id == provider_id).all()
    return {
        "provider_id": provider_id,
        "models": [
            {
                "id": m.id,
                "model_identifier": m.model_identifier,
                "display_name": m.display_name,
                "is_available": m.is_available,
                "supports_tools": m.supports_tools,
                "supports_json": m.supports_json
            } for m in models
        ]
    }
