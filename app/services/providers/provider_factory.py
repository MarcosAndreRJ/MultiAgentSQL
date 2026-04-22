"""
Fábrica de Clientes de Provedores.
Resolve a instância operacional e a chave de API (Segregação/Cascata).
"""
from typing import Optional
from sqlalchemy.orm import Session

from app.db import models as db_models
from app.core.settings import settings
from app.services.providers.clients.base_provider_client import BaseProviderClient
from app.services.providers.clients.openai_provider_client import OpenAIProviderClient
from app.services.providers.clients.ollama_provider_client import OllamaProviderClient
from app.services.providers.clients.gemini_provider_client import GeminiProviderClient
from app.core.logger import get_logger

logger = get_logger("providers.factory")

def get_provider_client(provider: db_models.LLMProvider) -> BaseProviderClient:
    """
    Retorna a instância do cliente para o provider.
    Resolução de chave (RESOLUÇÃO CASCATA):
    1. Se o provider tiver credencial segura (futuro)
    2. Fallback via ENV de settings (desenvolvimento)
    """
    
    # 1. Busca chave real (Cascata de Resolução)
    # Tenta primeiro a chave persistida no banco, se não houver, usa Fallback via ENV.
    api_key_real: Optional[str] = getattr(provider, "api_key", None)
    p_type = provider.provider_type.lower()
    
    if p_type == "openai":
        api_key_real = api_key_real or settings.OPENAI_API_KEY
        return OpenAIProviderClient(api_key=api_key_real, base_url=provider.base_url)

    elif p_type == "ollama":
        # Ollama usa as configurações de URL e KEY do provider se existirem
        return OllamaProviderClient(base_url=provider.base_url, api_key=api_key_real)

    elif p_type == "gemini":
        api_key_real = api_key_real or settings.GEMINI_API_KEY
        return GeminiProviderClient(api_key=api_key_real, base_url=provider.base_url)

    elif p_type == "custom":
        # Provedores customizados geralmente são compatíveis com OpenAI (OpenRouter, etc)
        api_key_real = api_key_real or settings.OPENAI_API_KEY
        return OpenAIProviderClient(api_key=api_key_real, base_url=provider.base_url)

    elif p_type == "anthropic":
        logger.warning(f"Anthropic Client não implementado para Provider '{provider.name}'.")
        raise NotImplementedError("Cliente Anthropic ainda não disponível para execução.")

    else:
        logger.error(f"Tipo de provedor '{provider.provider_type}' não suportado na Etapa 4.2.")
        raise ValueError(f"Provedor '{p_type}' não suportado operacionalmente.")
