"""
Serviço de Gestão de Modelos de LLM.
Sincronização com provedores e listagem para o Dashboard.
"""
from typing import List, Optional
from sqlalchemy.orm import Session

from app.db.models import LLMModel, LLMProvider
from app.core.logger import get_logger
from app.schemas.model import ModelRead, ProviderCatalogRead
from app.services.providers.provider_factory import get_provider_client
from app.services.platform.provider_service import _to_read_model as provider_to_read

logger = get_logger("services.models")


async def get_all_models(db: Session, provider_id: Optional[int] = None) -> List[ModelRead]:
    """
    Retorna todos os modelos ativos cadastrados.
    Opcionalmente filtra por provedor.
    """
    query = db.query(LLMModel)
    if provider_id:
        query = query.filter(LLMModel.provider_id == provider_id)
    
    models = query.all()
    
    # Auto-sync se estiver vazio e houver providers
    if not models and not provider_id:
        active_providers = db.query(LLMProvider).filter(LLMProvider.is_active == True).count()
        if active_providers > 0:
            logger.info("Catalogo vazio detectado. Acionando auto-sync...")
            await sync_all_active_providers(db)
            models = db.query(LLMModel).all()

    result = []
    for m in models:
        provider_name = m.provider.name if m.provider else None
        
        result.append(ModelRead(
            id=m.id,
            model_id=m.model_identifier,
            display_name=m.display_name,
            provider_id=m.provider_id,
            provider_name=provider_name,
            context_window=m.context_window,
            supports_tools=m.supports_tools,
            supports_json=m.supports_json,
            supports_streaming=m.supports_streaming,
            is_available=m.is_available,
            is_active=m.is_active,
            status="active" if (m.is_available and m.is_active) else "inactive",
            source=m.source,
            created_at=m.created_at,
            updated_at=m.updated_at,
        ))
    
    return result


async def get_models_catalog(db: Session) -> List[ProviderCatalogRead]:
    """
    Retorna o catálogo de modelos agrupado por provider.
    Dados puros (JSON), sem HTML.
    """
    providers = db.query(LLMProvider).filter(LLMProvider.is_active == True).all()
    
    # Se não houver modelos, tenta sync
    model_count = db.query(LLMModel).count()
    if model_count == 0 and len(providers) > 0:
        await sync_all_active_providers(db)

    catalog = []
    for p in providers:
        # Pega modelos do provider
        models = db.query(LLMModel).filter(LLMModel.provider_id == p.id).all()
        model_reads = []
        for m in models:
            model_reads.append(ModelRead(
                id=m.id,
                model_id=m.model_identifier,
                display_name=m.display_name,
                provider_id=m.provider_id,
                provider_name=p.name,
                context_window=m.context_window,
                supports_tools=m.supports_tools,
                supports_json=m.supports_json,
                supports_streaming=m.supports_streaming,
                is_available=m.is_available,
                is_active=m.is_active,
                status="active" if (m.is_available and m.is_active) else "inactive",
                source=m.source,
                created_at=m.created_at,
                updated_at=m.updated_at,
            ))
        
        catalog.append(ProviderCatalogRead(
            provider=provider_to_read(p),
            models=model_reads
        ))
    
    return catalog

async def sync_provider_models(db: Session, provider_id: int):
    """
    Sincroniza os modelos técnicos de um provedor usando seu adapter.
    """
    from datetime import datetime
    provider = db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
    if not provider or not provider.is_active:
        return

    logger.info(f"Sincronizando modelos para provider {provider.name} (ID: {provider.id})")
    try:
        client = get_provider_client(provider)
        external_models = client.list_models() # Retorna lista de dicts: id, name, capabilities
        
        synced_ids = []
        for ext_m in external_models:
            model_id = ext_m["id"]
            synced_ids.append(model_id)
            
            existing = db.query(LLMModel).filter(
                LLMModel.provider_id == provider_id,
                LLMModel.model_identifier == model_id
            ).first()
            
            # Extrai capacidades se disponível no client
            caps = ext_m.get("capabilities", {})
            
            if existing:
                existing.is_available = True
                existing.updated_at = datetime.utcnow()
                # Atualiza capacidades se vierem no sync
                if caps:
                    existing.supports_tools = caps.get("tools", existing.supports_tools)
                    existing.supports_json = caps.get("json", existing.supports_json)
                    existing.supports_streaming = caps.get("streaming", existing.supports_streaming)
                    if "context_window" in caps:
                        existing.context_window = caps["context_window"]
            else:
                new_model = LLMModel(
                    provider_id=provider_id,
                    model_identifier=model_id,
                    display_name=ext_m.get("name", model_id),
                    is_available=True,
                    is_active=True,
                    supports_tools=caps.get("tools", False),
                    supports_json=caps.get("json", False),
                    supports_streaming=caps.get("streaming", True),
                    context_window=caps.get("context_window"),
                    source="sync"
                )
                db.add(new_model)
        
        # Marca como indisponíveis modelos que não vieram no sync
        db.query(LLMModel).filter(
            LLMModel.provider_id == provider_id,
            ~LLMModel.model_identifier.in_(synced_ids),
            LLMModel.source == "sync"
        ).update({"is_available": False}, synchronize_session=False)
        
        db.commit()
    except Exception as e:
        logger.error(f"Falha ao sincronizar provider {provider_id}: {e}")
        db.rollback()


async def sync_all_active_providers(db: Session):
    """Sincroniza todos os provedores ativos."""
    providers = db.query(LLMProvider).filter(LLMProvider.is_active == True).all()
    for p in providers:
        await sync_provider_models(db, p.id)


async def bootstrap_models(db: Session):
    """
    Garante que os modelos mínimos existam.
    """
    await sync_all_active_providers(db)
