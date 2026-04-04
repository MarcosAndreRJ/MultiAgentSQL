"""
LLM Provider Factory — Cria o provider correto a partir da configuração do agente.
Suporta fallback automático entre providers.
"""
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.schemas.agent import AgentConfig
from app.schemas.chat import LLMPlan
from app.services.llm.base import LLMProvider, LLMProviderError

logger = get_logger("llm_factory")


def _build_provider(
    provider_name: str, 
    model: str, 
    timeout: int,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> LLMProvider:
    """Instancia o provider concreto pelo nome."""
    name = provider_name.lower()
    if name == "ollama":
        from app.services.llm.ollama import OllamaProvider
        return OllamaProvider(
            model=model, 
            timeout=timeout,
            base_url=base_url,
            api_key=api_key
        )
    elif name in ("gemini", "google"):
        from app.services.llm.gemini import GeminiProvider
        return GeminiProvider(model=model, timeout=timeout)
    else:
        raise ValueError(f"Provider desconhecido: '{provider_name}'. Use 'ollama' ou 'gemini'.")


class FallbackProvider(LLMProvider):
    """
    Provider com fallback automático.
    Tenta o provider primário. Se falhar (LLMProviderError), usa o secundário.
    """

    def __init__(self, primary: LLMProvider, fallback: LLMProvider):
        self._primary = primary
        self._fallback = fallback
        self.last_used_provider: Optional[str] = None
        self.fallback_was_used: bool = False
        self.fallback_from: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return self._primary.provider_name

    @property
    def model_name(self) -> str:
        return self._primary.model_name

    @property
    def timeout(self) -> int:
        return self._primary.timeout

    async def _call_with_fallback(self, primary_fn, fallback_fn):
        try:
            result = await primary_fn()
            self.last_used_provider = self._primary.provider_name
            self.fallback_was_used = False
            self.fallback_from = None
            return result
        except LLMProviderError as e:
            logger.warning(
                f"[LLM_PROVIDER_FALLBACK] Provider primário '{self._primary.provider_name}' falhou: {e}. "
                f"Tentando fallback '{self._fallback.provider_name}'..."
            )
            result = await fallback_fn()
            self.last_used_provider = self._fallback.provider_name
            self.fallback_was_used = True
            self.fallback_from = f"{self._primary.provider_name}/{self._primary.model_name}"
            logger.info(
                f"[LLM_PROVIDER_FALLBACK] Fallback bem-sucedido via '{self._fallback.provider_name}/{self._fallback.model_name}'"
            )
            return result

    async def chat_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        execution_id: Optional[str] = None,
        db: Optional["Session"] = None,
    ) -> str:
        return await self._call_with_fallback(
            lambda: self._primary.chat_async(prompt, system_prompt, temperature, execution_id=execution_id, db=db),
            lambda: self._fallback.chat_async(prompt, system_prompt, temperature, execution_id=execution_id, db=db),
        )

    async def get_plan_async(
        self,
        system_prompt: str,
        user_message: str,
        execution_id: Optional[str] = None,
        db: Optional["Session"] = None,
    ) -> LLMPlan:
        return await self._call_with_fallback(
            lambda: self._primary.get_plan_async(system_prompt, user_message, execution_id=execution_id, db=db),
            lambda: self._fallback.get_plan_async(system_prompt, user_message, execution_id=execution_id, db=db),
        )

    async def health_check(self) -> tuple[bool, str]:
        ok, msg = await self._primary.health_check()
        if ok:
            return True, f"[primary={self._primary.provider_name}] {msg}"
        ok_fb, msg_fb = await self._fallback.health_check()
        return ok_fb, f"[primary FAILED] {msg} | [fallback={self._fallback.provider_name}] {msg_fb}"


def get_provider(agent_config: AgentConfig) -> LLMProvider:
    """
    Retorna o provider de LLM correto baseado na configuração do agente.

    Prioridade:
    1. Se `agent_config.llm` estiver configurado, usa esses valores.
    2. Caso contrário, usa `agent_config.model` com provider Ollama (retrocompatível).
    3. Se `llm.fallback_provider` estiver configurado, envolve em FallbackProvider.
    """
    llm_cfg = getattr(agent_config, "llm", None)

    if llm_cfg is None:
        # Retrocompatibilidade: usa model do agente com Ollama
        logger.debug(f"[LLM_PROVIDER_SELECTED] Retrocompatível | provider=ollama | model={agent_config.model}")
        from app.services.llm.ollama import OllamaProvider
        from app.core.settings import settings
        return OllamaProvider(model=agent_config.model, timeout=settings.OLLAMA_TIMEOUT)

    primary_name = llm_cfg.provider or "ollama"
    primary_model = llm_cfg.model or agent_config.model
    primary_timeout = llm_cfg.timeout_seconds or 120
    primary_url = llm_cfg.base_url
    primary_key = llm_cfg.api_key

    logger.info(f"[LLM_PROVIDER_SELECTED] provider={primary_name} model={primary_model}")

    primary = _build_provider(
        primary_name, 
        primary_model, 
        primary_timeout, 
        base_url=primary_url, 
        api_key=primary_key
    )

    fb_name = llm_cfg.fallback_provider
    fb_model = llm_cfg.fallback_model
    if fb_name and fb_model:
        fallback = _build_provider(fb_name, fb_model, primary_timeout)
        logger.debug(f"[LLM_PROVIDER_FALLBACK_CONFIGURED] fallback={fb_name}/{fb_model}")
        return FallbackProvider(primary=primary, fallback=fallback)

    return primary
