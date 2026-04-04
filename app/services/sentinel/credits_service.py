"""
Service para Coleta de Créditos/Saldo de Provedores.
"""
from typing import Dict, Any

from app.db import models as db_models
from app.services.providers.provider_factory import get_provider_client
from app.core.logger import get_logger

logger = get_logger("sentinel.credits")


async def fetch_provider_credits(provider: db_models.LLMProvider) -> Dict[str, Any]:
    """
    Tenta coletar os créditos do provedor via seu cliente específico.

    Retorna status padronizado:
    - supported
    - unsupported
    - error
    """
    try:
        client = get_provider_client(provider)
        credits = await client.get_available_credits()

        if not isinstance(credits, dict):
            return {"amount": None, "currency": None, "status": "error", "details": "Formato de resposta inválido"}

        return {
            "amount": credits.get("amount"),
            "currency": credits.get("currency"),
            "status": credits.get("status", "unsupported"),
            "details": credits.get("details"),
        }
    except Exception as e:
        logger.error("Erro ao coletar créditos para %s: %s", provider.name, str(e))
        return {"amount": None, "currency": None, "status": "error", "details": str(e)}
