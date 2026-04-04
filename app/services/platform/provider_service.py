"""
Service layer para Providers (somente logica de negocio e acesso platform_db).
Atualizado para Etapa 4.2 Hardened (mapeia 'type' -> 'provider_type').

Regras:
- Nao chama APIs externas (usa clients indiretamente)
- Nao testa conexao real (usa test_provider_connection)
- Realiza validacoes estruturais e evita duplicidade logica
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import time

from app.db import models as db_models
from app.schemas.provider import ProviderCreate, ProviderUpdate, ProviderRead
from app.utils.secrets import mask_secret
from app.core.logger import get_logger
from app.services.providers.provider_factory import get_provider_client
from app.services.observability.execution_observability_service import (
    generate_execution_id,
    log_provider_execution,
)

logger = get_logger("services.platform.provider_service")


def _to_read_model(row: db_models.LLMProvider, include_key: bool = False) -> ProviderRead:
    """Mapeia do banco de dados (provider_type) para a API (type)."""
    return ProviderRead(
        id=row.id,
        name=row.name,
        type=row.provider_type, # Mapeamento: provider_type (DB) -> type (API)
        base_url=row.base_url,
        is_active=bool(row.is_active),
        config_json=getattr(row, "config_json", None) if hasattr(row, "config_json") else None,
        has_api_key=bool(getattr(row, "api_key", None)),
        api_key=row.api_key if include_key else None, # Real key include
        last_status=row.last_status,
        last_test_at=row.last_test_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def list_providers(db: Session) -> List[ProviderRead]:
    rows = db.query(db_models.LLMProvider).all()
    return [_to_read_model(r) for r in rows]


def get_provider(db: Session, provider_id: int) -> Optional[ProviderRead]:
    row = db.query(db_models.LLMProvider).filter(db_models.LLMProvider.id == provider_id).first()
    if not row:
        return None
    return _to_read_model(row, include_key=True)


def create_provider(db: Session, data: ProviderCreate) -> ProviderRead:
    # valida duplicidade logica: name + provider_type
    p_type = data.type.value if hasattr(data.type, 'value') else data.type
    
    # Validação adicional (além do Pydantic) para garantir base_url para custom
    if p_type == "custom" and not data.base_url:
        raise ValueError("O campo 'base_url' é obrigatório para provedores do tipo 'custom'")

    existing = db.query(db_models.LLMProvider).filter(
        db_models.LLMProvider.name == data.name,
        db_models.LLMProvider.provider_type == p_type,
    ).first()
    if existing:
        raise ValueError("Já existe um provider com este nome e tipo.")

    masked = mask_secret(data.api_key) if data.api_key else None
    logger.debug(f"Criando provider {data.name} (tipo: {p_type}, key: {masked})")

    row = db_models.LLMProvider(
        name=data.name,
        provider_type=p_type, # Mapeamento: type (API) -> provider_type (DB)
        base_url=data.base_url,
        api_key_masked=masked,
        api_key=data.api_key, # Persistência da chave real
        is_active=bool(data.is_active),
        source="manual",
    )

    db.add(row)
    try:
        db.commit()
        db.refresh(row)
    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError creating provider: {e}")
        raise

    return _to_read_model(row)


def update_provider(db: Session, provider_id: int, data: ProviderUpdate) -> Optional[ProviderRead]:
    row = db.query(db_models.LLMProvider).filter(db_models.LLMProvider.id == provider_id).first()
    if not row:
        return None

    if data.name is not None:
        row.name = data.name
    if data.type is not None:
        p_type = data.type.value if hasattr(data.type, 'value') else data.type
        row.provider_type = p_type
    if data.base_url is not None:
        row.base_url = data.base_url
    if data.is_active is not None:
        row.is_active = bool(data.is_active)
    if data.config_json is not None:
        logger.debug("config_json provided but not persisted (model lacks column)")
    if data.api_key is not None:
        row.api_key_masked = mask_secret(data.api_key)
        row.api_key = data.api_key # Atualiza a chave real

    row.updated_at = datetime.utcnow()
    try:
        db.commit()
        db.refresh(row)
    except IntegrityError:
        db.rollback()
        raise

    return _to_read_model(row)


def activate_provider(db: Session, provider_id: int) -> Optional[ProviderRead]:
    row = db.query(db_models.LLMProvider).filter(db_models.LLMProvider.id == provider_id).first()
    if not row:
        return None
    row.is_active = True
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _to_read_model(row)


def deactivate_provider(db: Session, provider_id: int) -> Optional[ProviderRead]:
    row = db.query(db_models.LLMProvider).filter(db_models.LLMProvider.id == provider_id).first()
    if not row:
        return None
    row.is_active = False
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _to_read_model(row)


# ── Operações Hardened (Etapa 4.2) ──────────────────────────────────
async def test_provider_connection(db: Session, provider_id: int) -> dict:
    """
    Testa a conexão real de um provedor de LLM.
    Governança: Bloqueia se inativo.
    """
    row = db.query(db_models.LLMProvider).filter(db_models.LLMProvider.id == provider_id).first()
    if not row:
        return {"status": "error", "error": "not_found", "details": "Provider não encontrado."}
        
    if not row.is_active:
        return {
            "status": "error", 
            "error": "inactive_provider", 
            "details": "Provider está desativado no sistema."
        }

    execution_id = generate_execution_id()
    start_time = time.time()

    try:
        client = get_provider_client(row)
        # Chamada assíncrona
        result = await client.test_connection()
        
        row.last_status = result["status"]
        row.last_test_at = datetime.utcnow()
        row.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(row)

        latency = float(result.get("latency_ms", 0.0) or 0.0)
        log_provider_execution(
            db,
            execution_id=execution_id,
            provider_id=row.id,
            model_id=None,
            operation="test_connection",
            status="success" if result["status"] == "ok" else "error",
            latency_ms=latency,
            error_message=result.get("details") if result["status"] != "ok" else None,
        )

        return {
            "execution_id": execution_id,
            "provider_id": provider_id,
            "status": result["status"],
            "latency_ms": result["latency_ms"],
            "error": result.get("error"),
            "details": result.get("details")
        }
    except Exception as e:
        row.last_status = "error"
        row.last_test_at = datetime.utcnow()
        db.commit()
        elapsed_ms = (time.time() - start_time) * 1000
        log_provider_execution(
            db,
            execution_id=execution_id,
            provider_id=row.id,
            model_id=None,
            operation="test_connection",
            status="error",
            latency_ms=elapsed_ms,
            error_message=str(e),
        )
        logger.error(f"Erro ao testar provider {provider_id}: {str(e)}")
        return {
            "execution_id": execution_id,
            "status": "error",
            "error": "internal_error",
            "details": "Falha crítica na comunicação com o provedor."
        }



async def sync_provider_models(db: Session, provider_id: int) -> dict:
    """
    Sincroniza os modelos técnicos do provedor com o banco local de forma assíncrona.
    Implementa SOFT-UPDATE (não deleta).
    """
    row = db.query(db_models.LLMProvider).filter(db_models.LLMProvider.id == provider_id).first()
    if not row:
        raise ValueError("Provider not found")
        
    if not row.is_active:
        raise ValueError(f"Provider '{row.name}' está inativo.")

    execution_id = generate_execution_id()
    start_time = time.time()

    try:
        client = get_provider_client(row)
        # Chamada assíncrona
        external_models = await client.list_models()
        
        synced_ids = []
        new_count = 0
        update_count = 0
        
        for ext_m in external_models:
            model_id = ext_m["id"]
            synced_ids.append(model_id)
            
            existing_m = db.query(db_models.LLMModel).filter(
                db_models.LLMModel.provider_id == provider_id,
                db_models.LLMModel.model_identifier == model_id
            ).first()
            
            if existing_m:
                existing_m.is_available = True
                existing_m.updated_at = datetime.utcnow()
                update_count += 1
            else:
                new_m = db_models.LLMModel(
                    provider_id=provider_id,
                    model_identifier=model_id,
                    display_name=model_id,
                    is_available=True,
                    source="sync"
                )
                db.add(new_m)
                new_count += 1
        
        missing_models = db.query(db_models.LLMModel).filter(
            db_models.LLMModel.provider_id == provider_id,
            ~db_models.LLMModel.model_identifier.in_(synced_ids)
        ).all()
        for missing in missing_models:
            missing.is_available = False
            
        db.commit()

        elapsed_ms = (time.time() - start_time) * 1000
        log_provider_execution(
            db,
            execution_id=execution_id,
            provider_id=row.id,
            model_id=None,
            operation="sync_models",
            status="success",
            latency_ms=elapsed_ms,
            error_message=None,
        )
        
        return {
            "execution_id": execution_id,
            "provider_id": provider_id,
            "models_synced": len(synced_ids),
            "new": new_count,
            "updated": update_count,
            "marked_unavailable": len(missing_models)
        }
        
    except Exception as e:
        db.rollback()
        elapsed_ms = (time.time() - start_time) * 1000
        log_provider_execution(
            db,
            execution_id=execution_id,
            provider_id=row.id,
            model_id=None,
            operation="sync_models",
            status="error",
            latency_ms=elapsed_ms,
            error_message=str(e),
        )
        logger.error(f"Erro no sync de modelos (Provider: {provider_id}): {str(e)}")
        raise

