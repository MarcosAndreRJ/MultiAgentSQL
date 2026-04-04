"""
Camada de modelos LLM no contexto do platform_db.
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import LLMModel
from app.services.dashboard import models_service as dashboard_models_service


async def list_platform_models(db: Session, provider_id: Optional[int] = None) -> list[LLMModel]:
    """Lista modelos LLM registrados no banco da plataforma."""

    return await dashboard_models_service.get_all_models(db, provider_id)
