"""
Cliente Gemini (Google).
Implementação simplificada para teste de conexão.
"""
import time
import httpx
from typing import List, Dict, Any, Optional

from app.services.providers.clients.base_provider_client import BaseProviderClient
from app.core.logger import get_logger

logger = get_logger("providers.clients.gemini")

class GeminiProviderClient(BaseProviderClient):
    def __init__(self, api_key: Optional[str], base_url: Optional[str] = None):
        self._api_key = api_key
        self.base_url = base_url or "https://generativelanguage.googleapis.com"

    async def test_connection(self) -> Dict[str, Any]:
        """Testa se a API do Gemini está acessível de forma assíncrona."""
        start_time = time.time()
        
        # Teste básico de reachability ou list models se houver chave
        url = f"{self.base_url}/v1beta/models?key={self._api_key}" if self._api_key else self.base_url
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url)
                latency = (time.time() - start_time) * 1000
                
                if response.status_code in [200, 401, 403]: 
                    # 401/403 indica que chegamos no Google, mas a chave é inválida/ausente
                    status = "ok" if response.status_code == 200 else "error"
                    err = None if status == "ok" else "authentication_error"
                    
                    return {
                        "status": status,
                        "latency_ms": round(latency, 2),
                        "error": err,
                        "details": "API Gemini alcançada." if status == "ok" else "API alcançada, mas credenciais falharam."
                    }
                
                return {
                    "status": "error",
                    "latency_ms": round(latency, 2),
                    "error": "connection_error",
                    "details": f"Status inesperado: {response.status_code}"
                }
        except Exception as e:
            return {
                "status": "error",
                "latency_ms": -1,
                "error": "internal_error",
                "details": str(e)
            }

    async def list_models(self) -> List[Dict[str, Any]]:
        """
        Lista modelos do Gemini com tratamento defensivo.
        """
        # Placeholder for real Gemini sync logic
        raw_list = [{"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro"}]
        
        models = []
        for m in raw_list:
            # ── Defensiva similar ao OpenAI para consistência ──
            m_id = getattr(m, 'id', None)
            if m_id is None and isinstance(m, dict):
                m_id = m.get('id')
            
            if m_id:
                models.append({
                    "id": str(m_id),
                    "name": getattr(m, 'name', m.get('name', str(m_id)))
                })
        
        return models

    async def get_available_credits(self) -> Dict[str, Any]:
        """Gemini (Google) não expõe saldo via API GenerativeLanguage facilmente."""
        return {"amount": None, "currency": None, "status": "unsupported"}

