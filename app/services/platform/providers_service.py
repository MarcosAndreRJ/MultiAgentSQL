"""
Camada de providers no contexto do platform_db.
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import LLMProvider
from app.services.dashboard import providers_service as dashboard_providers_service


async def list_platform_providers(db: Session) -> list[LLMProvider]:
    """Lista providers cadastrados no banco da plataforma."""

    return await dashboard_providers_service.get_all_providers(db)


async def get_platform_provider(db: Session, provider_id: int) -> Optional[LLMProvider]:
    """Retorna um provider específico do platform_db."""

    return await dashboard_providers_service.get_provider_by_id(db, provider_id)
