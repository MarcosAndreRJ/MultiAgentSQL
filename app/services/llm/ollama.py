"""
Ollama LLM Provider — Wrapper do cliente Ollama existente na interface LLMProvider.
"""
from typing import Optional

import httpx

from app.core.logger import get_logger
from app.core.settings import settings
from app.schemas.chat import LLMPlan
from app.services.llm.base import LLMProvider, LLMProviderError
from app.services import ollama_client

logger = get_logger("llm_provider.ollama")


class OllamaProvider(LLMProvider):
    """Provider que chama o Ollama local ou cloud (compatível)."""

    def __init__(
        self, 
        model: str, 
        timeout: Optional[int] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self._model = model
        self._timeout = timeout or settings.OLLAMA_TIMEOUT
        self._base_url = base_url
        self._api_key = api_key

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def timeout(self) -> int:
        return self._timeout

    async def chat_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
    ) -> str:
        try:
            logger.info(f"[LLM_PROVIDER_SELECTED] provider=ollama model={self._model}")
            
            # Construir argumentos dinâmicos para evitar TypeError em hot-reload parcial
            kwargs = {
                "model": self._model,
                "prompt": prompt,
                "system_prompt": system_prompt,
                "temperature": temperature,
                "timeout": self._timeout
            }
            if self._base_url:
                kwargs["base_url"] = self._base_url
            if self._api_key:
                kwargs["api_key"] = self._api_key
            elif settings.OLLAMA_CLOUD_API_KEY:
                kwargs["api_key"] = settings.OLLAMA_CLOUD_API_KEY

            result = await ollama_client.chat_async(**kwargs)
            return result
        except ollama_client.OllamaError as e:
            raise LLMProviderError("ollama", str(e)) from e

    async def get_plan_async(
        self,
        system_prompt: str,
        user_message: str,
    ) -> LLMPlan:
        try:
            logger.info(f"[LLM_PROVIDER_SELECTED] provider=ollama model={self._model}")
            
            # Construir argumentos dinâmicos
            kwargs = {
                "model": self._model,
                "system_prompt": system_prompt,
                "user_message": user_message
            }
            if self._base_url:
                kwargs["base_url"] = self._base_url
            if self._api_key:
                kwargs["api_key"] = self._api_key
            elif settings.OLLAMA_CLOUD_API_KEY:
                kwargs["api_key"] = settings.OLLAMA_CLOUD_API_KEY

            return await ollama_client.get_plan_async(**kwargs)
        except ollama_client.OllamaError as e:
            raise LLMProviderError("ollama", str(e)) from e

    async def health_check(self) -> tuple[bool, str]:
        return await ollama_client.check_connection()
