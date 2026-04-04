"""
Interface Base para Clientes de Provedores LLM.
Garante que todos os provedores (OpenAI, Anthropic, etc) implementem os mesmos métodos operacionais.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseProviderClient(ABC):
    
    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """
        Realiza um teste real de conectividade e autenticação.
        Retorno padronizado: {"status": "ok"|"error", "latency_ms": float, "error": str|None}
        """
        pass

    @abstractmethod
    async def list_models(self) -> List[Dict[str, Any]]:
        """
        Retorna a lista de modelos disponíveis no provedor.
        Retorno: Lista de dicts com id (mínimo).
        """
        pass

    @abstractmethod
    async def get_available_credits(self) -> Dict[str, Any]:
        """
        Retorna o saldo/créditos disponíveis no provedor.
        Retorno: {"amount": float | None, "currency": str | None, "status": "supported" | "unsupported"}
        """
        pass

