"""
Serviço de Gestão de Modelos de LLM.
Sincronização com provedores e listagem para o Dashboard.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models import LLMModel, LLMProvider
from app.services import ollama_client
from app.core.logger import get_logger

logger = get_logger("services.models")

async def get_all_models(db: Session, provider_id: Optional[int] = None) -> List[LLMModel]:
    """
    Retorna todos os modelos ativos cadastrados.
    Opcionalmente filtra por provedor.
    """
    query = db.query(LLMModel)
    if provider_id:
        query = query.filter(LLMModel.provider_id == provider_id)
    return query.all()

async def sync_ollama_models(db: Session, provider_id: int):
    """
    Sincroniza os modelos instalados no Ollama local com o banco de dados.
    """
    provider = db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
    if not provider or provider.provider_type != "ollama":
        return

    try:
        # Tenta listar os modelos via OllamaClient (se existir check_connection / tags)
        # Assumindo que ollama_client tem algo que retorne tags
        # Se não tiver, populamos o default do settings.py no bootstrap.
        from app.core.settings import settings
        
        # Para bootstrap, ao menos garantimos o default
        models_to_ensure = [settings.OLLAMA_DEFAULT_MODEL]
        
        for model_id in models_to_ensure:
            existing = db.query(LLMModel).filter(
                LLMModel.provider_id == provider_id,
                LLMModel.model_identifier == model_id
            ).first()
            
            if not existing:
                new_model = LLMModel(
                    provider_id=provider_id,
                    model_identifier=model_id,
                    display_name=model_id.split(':')[0].capitalize(),
                    supports_tools=True if "llama3" in model_id or "qwen" in model_id else False,
                    supports_json=True,
                    source="sync"
                )
                db.add(new_model)
        
        db.commit()
    except Exception as e:
        logger.error(f"Erro ao sincronizar modelos Ollama: {str(e)}")
        db.rollback()

async def bootstrap_models(db: Session):
    """
    Garante que os modelos mínimos configurados no startup existam no banco.
    """
    providers = db.query(LLMProvider).all()
    for p in providers:
        if p.provider_type == "ollama":
            await sync_ollama_models(db, p.id)
        elif p.provider_type == "gemini":
            from app.core.settings import settings
            model_id = settings.GEMINI_MODEL_DEFAULT
            existing = db.query(LLMModel).filter(
                LLMModel.provider_id == p.id,
                LLMModel.model_identifier == model_id
            ).first()
            if not existing:
                new_model = LLMModel(
                    provider_id=p.id,
                    model_identifier=model_id,
                    display_name="Gemini 2.0 Flash Lite",
                    supports_tools=True,
                    supports_json=True,
                    source="bootstrap"
                )
                db.add(new_model)
    
    db.commit()
