"""
API Routes: Providers
GET /api/providers - listar providers
GET /api/providers/{id} - detalhar provider
PUT /api/providers/{id} - atualizar provider
DELETE /api/providers/{id} - excluir provider
POST /api/providers/{id}/test - testar conexão
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Dict, List

from app.db.session import get_db
from app.services.dashboard import providers_service
from app.services import ollama_client

router = APIRouter(prefix="/api/providers", tags=["dashboard", "providers"])

@router.get("/")
async def list_providers(db: Session = Depends(get_db)):
    """Lista todos os providers de LLM ativos no banco."""
    providers = await providers_service.get_all_providers(db)
    return {"providers": providers}

@router.get("/{provider_id}")
async def get_provider(provider_id: int, db: Session = Depends(get_db)):
    """Detalhes de um provider específico."""
    provider = await providers_service.get_provider_by_id(db, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider não encontrado")
    return provider

@router.put("/{provider_id}")
async def update_provider(provider_id: int, data: Dict = Body(...), db: Session = Depends(get_db)):
    """Atualiza dados amigáveis de um provider."""
    provider = await providers_service.update_provider(db, provider_id, data)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider não encontrado")
    return provider

@router.delete("/{provider_id}")
async def delete_provider(provider_id: int, db: Session = Depends(get_db)):
    """Remove um provider do banco."""
    success = await providers_service.delete_provider(db, provider_id)
    if not success:
        raise HTTPException(status_code=404, detail="Provider não encontrado")
    return {"status": "ok", "message": "Provider excluído com sucesso"}

@router.post("/{provider_id}/test")
async def test_provider(provider_id: int, db: Session = Depends(get_db)):
    """Testa a conectividade com o provider de LLM."""
    provider = await providers_service.get_provider_by_id(db, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider não encontrado")
    
    # Simula o teste dependendo do tipo
    if provider.provider_type == "ollama":
        # Poderia usar p.base_url se o ollama_client suportasse override de host
        # Para esta fase, testamos o default configurado
        ok, msg = await ollama_client.check_connection()
        return {"ok": ok, "message": msg}
    elif provider.provider_type == "gemini":
        from app.core.settings import settings
        if settings.GEMINI_API_KEY:
            return {"ok": True, "message": "API Key configurada (Google Cloud)"}
        return {"ok": False, "message": "GEMINI_API_KEY não encontrada no servidor."}
        
    return {"ok": False, "message": "Provider selecionado não suporta este teste automatizado."}
