"""
LLM Provider — Interface base abstrata.
Todo provider deve implementar esta interface.
"""
from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from app.schemas.chat import LLMPlan


class LLMProvider(ABC):
    """Interface abstrata para qualquer provider de LLM."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Nome do provider (ex: 'ollama', 'gemini')."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Modelo usado por este provider."""

    @property
    @abstractmethod
    def timeout(self) -> int:
        """Timeout em segundos."""

    @abstractmethod
    async def chat_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        execution_id: Optional[str] = None,
        db: Optional["Session"] = None,
    ) -> str:
        """
        Envia prompt e retorna a resposta como string bruta.

        Raises:
            LLMProviderError: Em caso de falha de comunicação.
        """

    @abstractmethod
    async def get_plan_async(
        self,
        system_prompt: str,
        user_message: str,
        execution_id: Optional[str] = None,
        db: Optional["Session"] = None,
    ) -> LLMPlan:
        """
        Solicita um plano estruturado (JSON) para o pipeline de execução.

        Returns:
            LLMPlan validado ou plano de fallback.
        """

    @abstractmethod
    async def health_check(self) -> tuple[bool, str]:
        """
        Verifica se o provider está disponível.

        Returns:
            (disponivel: bool, mensagem: str)
        """


class LLMProviderError(Exception):
    """Erro genérico de comunicação com um LLM provider."""

    def __init__(self, provider: str, message: str):
        self.provider = provider
        super().__init__(f"[{provider}] {message}")
