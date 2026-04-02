"""
Serviço de Gestão de Providers de LLM.
Lógica de persistência e bootstrap inicial a partir das configurações.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.models import LLMProvider, LLMModel
from app.core.settings import settings
from app.core.logger import get_logger

logger = get_logger("services.providers")

async def get_all_providers(db: Session) -> List[LLMProvider]:
    """
    Retorna todos os provedores ativos cadastrados no banco.
    """
    return db.query(LLMProvider).filter(LLMProvider.is_active == True).all()

async def get_provider_by_id(db: Session, provider_id: int) -> Optional[LLMProvider]:
    """
    Retorna um provedor específico pelo ID.
    """
    return db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()

async def create_provider(db: Session, data: dict) -> LLMProvider:
    """
    Cria um novo provedor no banco de dados.
    """
    provider = LLMProvider(
        name=data.get("name"),
        provider_type=data.get("provider_type"),
        base_url=data.get("base_url"),
        api_key_masked=data.get("api_key_masked"),
        source=data.get("source", "live")
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider

async def update_provider(db: Session, provider_id: int, data: dict) -> Optional[LLMProvider]:
    """
    Atualiza dados de um provedor de LLM.
    """
    provider = db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
    if not provider:
        return None
    
    if "name" in data:
        provider.name = data["name"]
    if "base_url" in data:
        provider.base_url = data["base_url"]
    if "is_active" in data:
        provider.is_active = data["is_active"]
    
    db.commit()
    db.refresh(provider)
    return provider

async def delete_provider(db: Session, provider_id: int) -> bool:
    """
    Remove ou inativa um provedor.
    """
    provider = db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
    if not provider:
        return False
    
    db.delete(provider)
    db.commit()
    return True

async def bootstrap_providers(db: Session):
    """
    Popula o banco de dados com os provedores configurados em settings.py
    se as tabelas estiverem vazias.
    """
    count = db.query(LLMProvider).count()
    if count > 0:
        return # Já populado

    logger.info("Executando bootstrap inicial de providers a partir do settings.py")
    
    # 1. Ollama (Local)
    ollama = LLMProvider(
        name="Ollama (Local Default)",
        provider_type="ollama",
        base_url=settings.OLLAMA_BASE_URL,
        is_active=True,
        source="bootstrap"
    )
    db.add(ollama)
    
    # 2. Gemini (Se houver API_KEY)
    if settings.GEMINI_API_KEY:
        gemini = LLMProvider(
            name="Google Gemini (Cloud)",
            provider_type="gemini",
            base_url="https://generativelanguage.googleapis.com", 
            api_key_masked="EXISTS" if settings.GEMINI_API_KEY else None,
            is_active=True,
            source="bootstrap"
        )
        db.add(gemini)

    try:
        db.commit()
        logger.info("Bootstrap de providers concluído com sucesso.")
    except Exception as e:
        logger.error(f"Erro durante bootstrap de providers: {str(e)}")
        db.rollback()
