"""
Gemini LLM Provider — Integração com Google Gemini Developer API (free tier).
Usa chamadas HTTP puras sem SDK para máxima portabilidade.
"""
import json
import re
import time
from typing import Optional

import httpx

from app.core.logger import get_logger
from app.core.settings import settings
from app.schemas.chat import LLMPlan
from app.services.llm.base import LLMProvider, LLMProviderError
from app.services.observability.execution_observability_service import log_provider_execution
from sqlalchemy.orm import Session

logger = get_logger("llm_provider.gemini")

# Instrução de planning estruturado (mesma que o Ollama usa)
_PLANNING_INSTRUCTION = """
Você DEVE responder APENAS com um JSON válido, sem texto adicional, sem markdown, sem ```json.
O JSON deve seguir exatamente este formato:

{
  "intent": "query|write|ddl|explain|mockdata|unknown",
  "needs_tools": true|false,
  "tools": [
    {
      "name": "db_introspect|db_execute|db_mockdata",
      "action": "EXATAMENTE UM DOS VALORES ABAIXO (sem tradução, sem espaço, snake_case):",
      "input": {}
    }
  ],
  "sql": "SQL gerado ou null",
  "explanation": "Explicação detalhada. IMPORTANTE: Quando needs_tools=false, escreva AQUI as respostas extraídas, pois o usuário só verá este texto final.",
  "risk_hint": "low|medium|high"
}

Valores válidos de 'action' para db_introspect:
  list_tables | list_views | list_triggers | list_procedures | list_functions
  describe_table | show_create_table | show_create_view | show_create_trigger
  show_create_procedure | show_create_function
  get_columns | get_indexes | get_foreign_keys | get_database_info

ATENÇÃO: Use SOMENTE os nomes de action listados acima, EXATAMENTE como escritos.
NÃO traduza para português. NÃO invente nomes. NÃO use espaços.

Se não precisar de tools, retorne needs_tools: false e lista vazia.
REGRAS DOURADAS PARA A EXPLICAÇÃO FINAL:
Se as ferramentas trouxeram dados, E você fará o needs_tools=false, transcreva/resuma os dados no campo "explanation".

CRÍTICO — SOBRE O HISTÓRICO:
O histórico da conversa mostra interações ANTERIORES, não os dados desta execução atual.
- SEMPRE use needs_tools=true e execute a ferramenta adequada para consultas ao banco
- NÃO considere respostas do histórico como dados já obtidos agora
- SOMENTE use needs_tools=false se houver um bloco "RESULTADO DE FERRAMENTA" no contexto

Responda APENAS o JSON, sem nenhum texto antes ou depois.
"""


class GeminiProvider(LLMProvider):
    """Provider que chama a API Google Gemini (Developer free tier)."""

    def __init__(
        self,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
        api_key: Optional[str] = None,
    ):
        self._model = model or settings.GEMINI_MODEL_DEFAULT
        self._timeout = timeout or settings.GEMINI_TIMEOUT_SECONDS
        self._api_key = api_key or settings.GEMINI_API_KEY

        if not self._api_key:
            raise LLMProviderError(
                "gemini",
                "GEMINI_API_KEY não configurada. Defina a variável de ambiente GEMINI_API_KEY."
            )

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def timeout(self) -> int:
        return self._timeout

    def _build_url(self, endpoint: str) -> str:
        base = settings.GEMINI_BASE_URL.rstrip("/")
        return f"{base}/models/{self._model}:{endpoint}?key={self._api_key}"

    def _build_payload(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
    ) -> dict:
        parts = [{"text": prompt}]
        payload: dict = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 4096,
            },
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        return payload

    def _extract_text(self, data: dict) -> str:
        """Extrai o texto da resposta da API Gemini."""
        try:
            candidates = data.get("candidates", [])
            if not candidates:
                raise LLMProviderError("gemini", "Nenhum candidate na resposta.")
            content = candidates[0].get("content", {})
            text_parts = content.get("parts", [])
            return "".join(p.get("text", "") for p in text_parts)
        except (KeyError, IndexError) as e:
            raise LLMProviderError("gemini", f"Falha ao extrair texto da resposta: {e}") from e

    async def chat_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        execution_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> str:
        url = self._build_url("generateContent")
        payload = self._build_payload(prompt, system_prompt, temperature)

        logger.info(f"[GEMINI_REQUEST] model={self._model} prompt_len={len(prompt)} execution_id={execution_id}")
        t0 = time.monotonic()
        status = "success"
        err_msg = None

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                text = self._extract_text(data)
                latency_ms = (time.monotonic() - t0) * 1000
                logger.info(f"[GEMINI_RESPONSE] latency={latency_ms:.0f}ms response_len={len(text)}")
                return text

        except httpx.TimeoutException:
            status = "error"
            err_msg = f"Timeout ({self._timeout}s)"
            logger.error(f"[GEMINI_TIMEOUT] model={self._model} timeout={self._timeout}s")
            raise LLMProviderError("gemini", f"Timeout ({self._timeout}s) aguardando resposta do Gemini.")
        except httpx.HTTPStatusError as e:
            status = "error"
            body = e.response.text[:300]
            err_msg = f"HTTP {e.response.status_code}: {body}"
            logger.error(f"[GEMINI_ERROR] HTTP {e.response.status_code}: {body}")
            raise LLMProviderError("gemini", f"Erro HTTP {e.response.status_code}: {body}") from e
        except LLMProviderError as e:
            status = "error"
            err_msg = str(e)
            raise
        except Exception as e:
            status = "error"
            err_msg = str(e)
            logger.error(f"[GEMINI_ERROR] Inesperado: {e}")
            raise LLMProviderError("gemini", f"Erro inesperado: {e}") from e
        finally:
            if db and execution_id:
                latency = (time.monotonic() - t0) * 1000
                log_provider_execution(
                    db=db,
                    execution_id=execution_id,
                    provider_id="gemini",
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
        full_system = f"{system_prompt}\n\n{_PLANNING_INSTRUCTION}"
        raw = await self.chat_async(
            prompt=user_message,
            system_prompt=full_system,
            temperature=0.05,
            execution_id=execution_id,
            db=db,
        )
        return _parse_gemini_plan(raw)

    async def health_check(self) -> tuple[bool, str]:
        try:
            text = await self.chat_async("Responda apenas 'ok'.", temperature=0.0)
            return True, f"Gemini disponível. Modelo: {self._model}. Resposta: {text[:50]}"
        except LLMProviderError as e:
            return False, str(e)


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


def _parse_gemini_plan(raw_response: str) -> LLMPlan:
    """Faz parse e validação da resposta JSON do Gemini (reutiliza lógica do ollama_client)."""
    if not raw_response or not raw_response.strip():
        logger.warning("[GEMINI] Resposta vazia do Gemini")
        return _fallback_plan("Resposta vazia do Gemini")

    text = raw_response.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)
    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                logger.warning(f"[GEMINI] JSON inválido na resposta: {text[:200]}")
                return _fallback_plan(text)
        else:
            logger.warning(f"[GEMINI] Nenhum JSON encontrado: {text[:200]}")
            return _fallback_plan(text)

    intent = data.get("intent", "unknown")
    if intent not in ("query", "write", "ddl", "explain", "mockdata", "unknown"):
        intent = "unknown"

    risk_hint = data.get("risk_hint", "low")
    if risk_hint not in ("low", "medium", "high"):
        risk_hint = "low"

    needs_tools = bool(data.get("needs_tools", False))
    tools = data.get("tools", [])
    if not isinstance(tools, list):
        tools = []
    tools = _normalize_tools(tools)

    sql = data.get("sql")
    if sql and not isinstance(sql, str):
        sql = str(sql)
    if sql:
        sql = sql.strip()
    if not sql:
        sql = None

    explanation = data.get("explanation") or ""
    if not isinstance(explanation, str):
        explanation = str(explanation)

    from pydantic import ValidationError
    try:
        return LLMPlan(
            intent=intent,
            needs_tools=needs_tools,
            tools=tools,
            sql=sql,
            explanation=explanation,
            risk_hint=risk_hint,
        )
    except ValidationError as ve:
        logger.warning(f"[GEMINI] Erro de validação no LLMPlan: {ve}")
        return LLMPlan(
            intent=intent or "unknown",
            needs_tools=needs_tools or False,
            tools=tools or [],
            sql=sql,
            explanation=explanation or "",
            risk_hint=risk_hint or "low"
        )


def _fallback_plan(text: str) -> LLMPlan:
    return LLMPlan(
        intent="explain",
        needs_tools=False,
        tools=[],
        sql=None,
        explanation=text,
        risk_hint="low",
    )
