"""
Cliente Ollama (Wrapper para BaseProviderClient).
Integra com o serviço legado app.services.ollama_client.
"""
import time
import asyncio
from typing import List, Dict, Any

from app.services.providers.clients.base_provider_client import BaseProviderClient
from app.services import ollama_client
from app.core.logger import get_logger

logger = get_logger("providers.clients.ollama")

class OllamaProviderClient(BaseProviderClient):
    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = base_url
        self.api_key = api_key

    async def test_connection(self) -> Dict[str, Any]:
        """Wrapper assíncrono para o check_connection."""
        start_time = time.time()
        try:
            # Uso direto do await no serviço assíncrono
            is_ok, msg = await ollama_client.check_connection()
            
            latency = (time.time() - start_time) * 1000
            
            if is_ok:
                return {
                    "status": "ok",
                    "latency_ms": round(latency, 2),
                    "details": msg
                }
            else:
                return {
                    "status": "error",
                    "latency_ms": round(latency, 2),
                    "error": "connection_failed",
                    "details": msg
                }
        except Exception as e:
            logger.error(f"Erro no teste de conexão Ollama: {str(e)}")
            return {
                "status": "error",
                "latency_ms": -1,
                "error": "internal_error",
                "details": str(e)
            }

    async def list_models(self) -> List[Dict[str, Any]]:
        """Busca modelos do Ollama de forma assíncrona."""
        try:
            models = await ollama_client.list_models()
            return [{"id": m, "name": m} for m in models]
        except Exception as e:
            logger.error(f"Erro ao listar modelos Ollama: {str(e)}")
            return []

    async def get_available_credits(self) -> Dict[str, Any]:
        """Ollama é local e não possui sistema de créditos."""
        return {"amount": None, "currency": None, "status": "unsupported"}

