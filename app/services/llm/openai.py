"""
OpenAI LLM Provider — Implementação operacional para chat e execução de planos.
Compatível com OpenAI oficial, Groq, OpenRouter e outros providers padrão OpenAI.
"""
from typing import Optional, Any
import time
from sqlalchemy.orm import Session
from openai import AsyncOpenAI

from app.core.logger import get_logger
from app.core.settings import settings
from app.schemas.chat import LLMPlan
from app.services.llm.base import LLMProvider, LLMProviderError
from app.services.observability.execution_observability_service import log_provider_execution

logger = get_logger("llm_provider.openai")

# Ações conhecidas de introspecção de banco
_INTROSPECT_ACTIONS = {
    "list_tables", "list_views", "list_triggers", "list_procedures", "list_functions",
    "describe_table", "show_create_table", "show_create_view", "show_create_trigger",
    "show_create_procedure", "show_create_function",
    "get_columns", "get_indexes", "get_foreign_keys", "get_database_info",
}
_TOOL_NAMES = {"db_introspect", "db_introspection", "db_execute", "db_mockdata"}


def _normalize_tools(raw: list) -> list[dict]:
    """
    Normaliza a lista de tools recebida do LLM.
    Modelos às vezes retornam strings no lugar de dicts.
    Ex: ["list_tables"] → [{"name": "db_introspect", "action": "list_tables", "input": {}}]
    """
    normalized = []
    for item in raw:
        if isinstance(item, dict):
            normalized.append(item)
        elif isinstance(item, str):
            item = item.strip()
            if item in _INTROSPECT_ACTIONS:
                normalized.append({"name": "db_introspect", "action": item, "input": {}})
                logger.debug(f"[TOOLS_NORMALIZE] String '{item}' convertida para db_introspect action.")
            elif item in _TOOL_NAMES:
                normalized.append({"name": item, "action": "", "input": {}})
                logger.debug(f"[TOOLS_NORMALIZE] String '{item}' convertida para tool name.")
            else:
                logger.warning(f"[TOOLS_NORMALIZE] Item de tool desconhecido ignorado: '{item}'")
        else:
            logger.warning(f"[TOOLS_NORMALIZE] Item de tool com tipo inválido ignorado: {type(item).__name__}")
    return normalized


class OpenAIProvider(LLMProvider):
    """Provider que utiliza o SDK oficial da OpenAI de forma assíncrona."""

    def __init__(
        self, 
        model: str, 
        timeout: Optional[int] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self._model = model
        self._timeout = timeout or 120
        self._base_url = base_url
        self._api_key = api_key or settings.OPENAI_API_KEY
        
        # Inicializa o cliente interno
        self.client = AsyncOpenAI(
            api_key=self._api_key or "NO_KEY",
            base_url=self._base_url
        )

    @property
    def provider_name(self) -> str:
        return "openai"

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
            logger.info(f"[LLM_PROVIDER_SELECTED] provider=openai model={self._model} execution_id={execution_id}")
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = await self.client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
                timeout=self._timeout
            )
            
            return response.choices[0].message.content or ""
            
        except Exception as e:
            status = "error"
            err_msg = str(e)
            logger.error(f"[LLM_PROVIDER_ERROR] openai: {err_msg}")
            raise LLMProviderError("openai", err_msg) from e
        finally:
            if db and execution_id:
                latency = (time.monotonic() - _t0) * 1000
                log_provider_execution(
                    db=db,
                    execution_id=execution_id,
                    provider_id=None,
                    model_id=None,
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
        """
        Executa a geração de plano estruturado.
        Nota: Para OpenAI, usamos response_format={"type": "json_object"}, 
        que EXIGE a palavra 'json' no prompt.
        """
        import json
        _t0 = time.monotonic()
        status = "success"
        err_msg = None
        content = None
        
        # Injeta instrução JSON se não estiver presente (exigência da API OpenAI para json_object)
        if "json" not in system_prompt.lower():
            system_prompt += "\n\nResponda estritamente em formato JSON válido."
        
        try:
            logger.info(f"[LLM_PROVIDER_SELECTED] provider=openai model={self._model} (PLAN) execution_id={execution_id}")
            
            response = await self.client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                response_format={"type": "json_object"},
                temperature=0,
                timeout=self._timeout
            )
            
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Resposta vazia do provedor de LLM.")
                
            from pydantic import ValidationError
            try:
                plan_data = json.loads(content)
                return LLMPlan(**plan_data)
            except (json.JSONDecodeError, ValidationError) as ve:
                logger.warning(f"[LLM_PROVIDER_PARSE_WARNING] Falha na validação rigorosa do plano: {ve}")
                if isinstance(ve, ValidationError):
                    data = json.loads(content)
                    # Usar 'or' para proteger contra campos com null explícito no JSON
                    raw_tools = data.get("tools") if isinstance(data.get("tools"), list) else []
                    return LLMPlan(
                        intent=data.get("intent") or "unknown",
                        needs_tools=bool(data.get("needs_tools") or False),
                        tools=_normalize_tools(raw_tools),
                        sql=data.get("sql") or None,
                        explanation=data.get("explanation") or "",
                        risk_hint=data.get("risk_hint") or "low"
                    )
                raise ve
            
        except Exception as e:
            status = "error"
            err_msg = str(e)
            logger.error(f"[LLM_PROVIDER_ERROR] openai (PLAN): {err_msg}")
            if content:
                logger.debug(f"[LLM_PROVIDER_RAW_CONTENT] Content failed to parse: {content}")
            
            # Tenta fallback se erro for de validação do JSON mode ou falha de parse
            if "json_object" in err_msg or "Expecting value" in err_msg or "vazia" in err_msg:
                 return await self._get_plan_fallback(system_prompt, user_message)
            raise LLMProviderError("openai", err_msg) from e
        finally:
            if db and execution_id:
                latency = (time.monotonic() - _t0) * 1000
                log_provider_execution(
                    db=db,
                    execution_id=execution_id,
                    provider_id=None,
                    model_id=None,
                    operation="get_plan",
                    status=status,
                    latency_ms=latency,
                    error_message=err_msg
                )

    async def _get_plan_fallback(self, system_prompt: str, user_message: str) -> LLMPlan:
        """Fallback para modelos que não suportam JSON mode ou falharam no parse inicial."""
        import json
        import re
        
        logger.info(f"[LLM_PROVIDER_FALLBACK] Iniciando fallback para {self._model}")
        
        response = await self.client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0,
            timeout=self._timeout
        )
        content = response.choices[0].message.content or ""
        
        # Tenta extrair JSON de blocos de código markdown ou texto livre
        json_match = re.search(r'```json\n?(.*?)\n?```', content, re.DOTALL)
        if json_match:
            content = json_match.group(1).strip()
        else:
            # Tenta encontrar algo que pareça um objeto JSON {}
            json_obj_match = re.search(r'({.*})', content, re.DOTALL)
            if json_obj_match:
                content = json_obj_match.group(1).strip()
        
        if not content or not content.strip():
            raise LLMProviderError("openai", "Falha crítica: O modelo não retornou um JSON válido no fallback.")
            
        try:
            plan_data = json.loads(content)
            return LLMPlan(**plan_data)
        except json.JSONDecodeError as je:
            logger.error(f"[LLM_PROVIDER_FALLBACK_ERROR] Falha final no parse: {content}")
            raise LLMProviderError("openai", f"Erro de parse no fallback: {str(je)}")

    async def health_check(self) -> tuple[bool, str]:
        """Tenta listar modelos como health check."""
        try:
            await self.client.models.list()
            return True, "OpenAI API alcançável."
        except Exception as e:
            return False, str(e)
