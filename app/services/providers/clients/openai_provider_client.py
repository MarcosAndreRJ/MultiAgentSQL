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
        Se for OpenRouter, filtra e sincroniza EXCLUSIVAMENTE modelos free.
        """
        try:
            base_url_str = str(self.client.base_url)
            
            # ── INTERCEPT EXCLUSIVO PARA OPENROUTER (Filtragem Free) ──
            if "openrouter.ai" in base_url_str:
                import httpx
                headers = {"Authorization": f"Bearer {self._api_key or ''}"}
                # Garante que não tenha url estourada (evita /models/models)
                url = base_url_str.rstrip('/')
                if not url.endswith("/models"):
                    url = f"{url}/models"
                    
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    
                models = []
                for m in data.get("data", []):
                    pricing = m.get("pricing", {})
                    try:
                        p_prompt = float(pricing.get("prompt", -1))
                        p_comp = float(pricing.get("completion", -1))
                        is_free = (p_prompt == 0.0 and p_comp == 0.0)
                    except (ValueError, TypeError):
                        is_free = False
                        
                    if is_free:
                        models.append({
                            "id": m.get("id"),
                            "owned_by": str(m.get("architecture", {}).get("tokenizer", "OpenRouter")),
                            "created": m.get("created")
                        })
                
                logger.info(f"OpenRouter Sync: Obtidos {len(models)} modelos GRATUITOS exclusivos.")
                return models

            # ── FLUXO PADRÃO OpenAI / Groq / Outros ──
            response = await self.client.models.list()
            
            models = []
            # ── 1. Extração robusta da lista de itens ──
            items = []
            
            # Se for o objeto padrão do SDK (SyncPage), acessamos .data
            if hasattr(response, "data") and isinstance(response.data, list):
                items = response.data
            # Se já for uma lista direta
            elif isinstance(response, list):
                items = response
            # Se for um dicionário (Provedores Custom/Groq as vezes retornam assim se o SDK falha no parse)
            elif isinstance(response, dict):
                items = response.get("data", [])
                if not isinstance(items, list): # Caso não tenha 'data' ou não seja lista
                    # Se for um dict mas não tem 'data', não iteramos sobre ele para evitar pegar chaves como IDs
                    items = []
                    logger.warning(f"Resposta de modelos em formato dict desconhecido: {list(response.keys())}")
            else:
                # Tenta iterar apenas se não for um objeto base
                try:
                    items = list(response)
                except:
                    items = []

            for m in items:
                # ── 2. Defensiva contra variacoes de modelo (objetos vs dicts) ──
                m_id = None
                owned_by = None
                created = None

                if isinstance(m, dict):
                    m_id = m.get('id')
                    owned_by = m.get('owned_by')
                    created = m.get('created')
                else:
                    m_id = getattr(m, 'id', None)
                    owned_by = getattr(m, 'owned_by', None)
                    created = getattr(m, 'created', None)
                
                # Se ainda nulo, tenta transformacao string (ultimo recurso)
                if m_id is None and m is not None:
                    if isinstance(m, str):
                        m_id = m

                if m_id and isinstance(m_id, str):
                    # Evita lixo técnicos do JSON de alguns provedores
                    if m_id.lower() in ("data", "object", "list", "model", "page"):
                        continue
                        
                    models.append({
                        "id": m_id,
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

