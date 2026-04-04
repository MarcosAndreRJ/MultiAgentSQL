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
from app.services.observability.execution_observability_service import log_provider_execution
import time
from sqlalchemy.orm import Session

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
        execution_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> str:
        _t0 = time.monotonic()
        status = "success"
        err_msg = None
        try:
            logger.info(f"[LLM_PROVIDER_SELECTED] provider=ollama model={self._model} execution_id={execution_id}")
            
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
            status = "error"
            err_msg = str(e)
            raise LLMProviderError("ollama", str(e)) from e
        finally:
            if db and execution_id:
                latency = (time.monotonic() - _t0) * 1000
                log_provider_execution(
                    db=db,
                    execution_id=execution_id,
                    provider_id="ollama",
                    model_id=self._model,
                    operation="chat",
                    status=status,
                    latency_ms=latency,
                    error_message=err_msg
                )

    async def get_plan_async(
        self,
        system_prompt: str,
        user_message: str,
        execution_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> LLMPlan:
        _t0 = time.monotonic()
        status = "success"
        err_msg = None
        try:
            logger.info(f"[LLM_PROVIDER_SELECTED] provider=ollama model={self._model} execution_id={execution_id}")
            
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
            status = "error"
            err_msg = str(e)
            raise LLMProviderError("ollama", str(e)) from e
        finally:
            if db and execution_id:
                latency = (time.monotonic() - _t0) * 1000
                log_provider_execution(
                    db=db,
                    execution_id=execution_id,
                    provider_id="ollama",
                    model_id=self._model,
                    operation="get_plan",
                    status=status,
                    latency_ms=latency,
                    error_message=err_msg
                )

    async def health_check(self) -> tuple[bool, str]:
        return await ollama_client.check_connection()
