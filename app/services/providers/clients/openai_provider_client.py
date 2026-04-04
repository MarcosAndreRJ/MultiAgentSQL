"""
Implementação Real do Cliente OpenAI.
Usa as regras de resolução de API Key (Cascata) e sanitização de erros.
"""
import time
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI, AuthenticationError, APIConnectionError

from app.services.providers.clients.base_provider_client import BaseProviderClient
from app.core.logger import get_logger
from app.utils.secrets import mask_api_key_for_logs

logger = get_logger("providers.openai")

class OpenAIProviderClient(BaseProviderClient):
    """
    Cliente operacional para interação com a OpenAI (Assíncrono).
    """
    def __init__(self, api_key: Optional[str], base_url: Optional[str] = None):
        self._api_key = api_key
        # Configuração da OpenAI (Usa o SDK oficial assíncrono)
        self.client = AsyncOpenAI(
            api_key=api_key or "NO_KEY",
            base_url=base_url
        )

    async def test_connection(self) -> Dict[str, Any]:
        """
        Executa um ping real (list_models) na OpenAI de forma assíncrona.
        """
        start_time = time.time()
        
        # 1. Verificação de chave nula antes de tentar
        if not self._api_key or self._api_key == "NO_KEY":
            return {
                "status": "error",
                "latency_ms": 0,
                "error": "authentication_error",
                "details": "Nenhuma API Key provida (nem no banco, nem no ambiente)."
            }

        try:
            # Operação mínima para teste: Listar modelos
            await self.client.models.list()
            
            latency = (time.time() - start_time) * 1000
            
            logger.info(f"OpenAI Saudável | Latência: {round(latency, 2)}ms")
            return {
                "status": "ok",
                "latency_ms": round(latency, 2),
                "error": None
            }
            
        except AuthenticationError:
            logger.error("Falha na autenticação OpenAI (Chave inválida).")
            return {
                "status": "error",
                "latency_ms": 0,
                "error": "authentication_error",
                "details": "Credenciais inválidas para o provedor OpenAI."
            }
        except APIConnectionError as e:
            logger.error(f"Erro de conexão OpenAI: {str(e)}")
            return {
                "status": "error",
                "latency_ms": 0,
                "error": "connection_error",
                "details": "Não foi possível alcançar a API da OpenAI."
            }
        except Exception as e:
            logger.error(f"Erro inesperado no cliente OpenAI: {str(e)}")
            return {
                "status": "error",
                "latency_ms": 0,
                "error": "internal_error",
                "details": "Erro interno ao processar requisição com o provedor."
            }

    async def list_models(self) -> List[Dict[str, Any]]:
        """
        Sincroniza a lista de modelos da OpenAI de forma assíncrona.
        """
        try:
            response = await self.client.models.list()
            
            models = []
            for m in response:
                # ── Defensiva contra variacoes de retorno (objetos vs dicts vs tuples) ──
                # 1. Tenta atributo (objeto SDK)
                m_id = getattr(m, 'id', None)
                owned_by = getattr(m, 'owned_by', None)
                created = getattr(m, 'created', None)

                # 2. Tenta chave (dicionário puro)
                if m_id is None and isinstance(m, dict):
                    m_id = m.get('id')
                    owned_by = m.get('owned_by')
                    created = m.get('created')
                
                # 3. Tenta índice (tupla) - caso extremo de driver quebrado
                if m_id is None and isinstance(m, (tuple, list)) and len(m) > 0:
                    m_id = m[0] # Assume que o ID é o primeiro elemento

                if m_id:
                    models.append({
                        "id": str(m_id),
                        "owned_by": str(owned_by) if owned_by else None,
                        "created": created
                    })

            return models
            
        except Exception as e:
            logger.error(f"Falha ao listar modelos OpenAI: {str(e)}")
            raise RuntimeError(f"Erro na sincronização de modelos: {str(e)}")

    async def get_available_credits(self) -> Dict[str, Any]:
        """OpenAI não expõe saldo facilmente via SDK sem permissões de admin/billing."""
        return {"amount": None, "currency": None, "status": "unsupported"}

