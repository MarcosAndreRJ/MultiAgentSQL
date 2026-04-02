"""
Ollama Client: cliente HTTP para comunicação com Ollama local.
Responsável por enviar prompts e receber respostas estruturadas.
"""
import json
import re
# v1.0.1 - Support for base_url and api_key
from typing import Optional

import httpx

from app.core.logger import get_logger
from app.core.settings import settings
from app.schemas.chat import LLMPlan

logger = get_logger("ollama_client")


class OllamaError(Exception):
    """Erro de comunicação com Ollama."""
    pass


async def chat_async(
    model: str,
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.1,
    timeout: Optional[int] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> str:
    """
    Envia prompt para Ollama e retorna a resposta como string.
    
    Args:
        model: Nome do modelo Ollama (ex: llama3.1:8b).
        prompt: Mensagem do usuário.
        system_prompt: System prompt (opcional).
        temperature: Temperatura de geração (baixa = mais determinístico).
        timeout: Timeout em segundos.
        
    Returns:
        Texto de resposta do modelo.
        
    Raises:
        OllamaError: Se Ollama não estiver disponível ou retornar erro.
    """
    _base = base_url or settings.OLLAMA_BASE_URL
    url = f"{_base.rstrip('/')}/api/chat"
    timeout_val = timeout or settings.OLLAMA_TIMEOUT
    _api_key = api_key or settings.OLLAMA_CLOUD_API_KEY

    headers = {}
    if _api_key:
        headers["Authorization"] = f"Bearer {_api_key}"
        logger.debug(f"[OLLAMA] Usando API Key (início: {_api_key[:4]}...)")

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": 4096,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_val, headers=headers) as client:
            logger.info("\n" + "="*60)
            logger.info(f"🔥 [OLLAMA REQUEST EXATO] | Modelo: {model}")
            for m in messages:
                logger.info(f"--- ROLE: {m['role']} ---")
                logger.info(f"{m['content']}")
            logger.info("="*60 + "\n")
            
            response = await client.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            content = data.get("message", {}).get("content", "")
            
            logger.info("\n" + "="*60)
            logger.info(f"🎯 [OLLAMA RESPONSE DEVOLVIDO EXATO]")
            logger.info(f"{content}")
            logger.info("="*60 + "\n")
            return content

    except httpx.ConnectError:
        logger.error("[OLLAMA ERROR] Não foi possível conectar ao provedor local.")
        raise OllamaError(
            f"Não foi possível conectar ao Ollama em {settings.OLLAMA_BASE_URL}. "
            "Verifique se o Ollama está rodando."
        )
    except httpx.TimeoutException:
        logger.error(f"[OLLAMA ERROR] Timeout ({timeout_val}s) no modelo {model}")
        raise OllamaError(
            f"Timeout ao aguardar resposta do Ollama (modelo={model}, timeout={timeout_val}s). "
            "Tente um modelo menor ou aumente o timeout."
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"[OLLAMA ERROR] HTTP {e.response.status_code}: {e.response.text}")
        raise OllamaError(f"Erro HTTP do Ollama: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        logger.error(f"[OLLAMA ERROR] Inesperado: {str(e)}")
        raise OllamaError(f"Erro inesperado com Ollama: {str(e)}")


async def get_plan_async(
    model: str,
    system_prompt: str,
    user_message: str,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> LLMPlan:
    """
    Solicita um plano estruturado (JSON) ao LLM.
    
    O sistema pede especificamente que o LLM retorne JSON estruturado.
    O backend valida e normaliza a resposta.
    
    Returns:
        LLMPlan validado ou plano de fallback.
    """
    planning_instruction = """
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
  "explanation": "Explicação detalhada. IMPORTANTE: Quando needs_tools=false, escreva AQUI as respostas extraídas (tabelas, esquemas, etc), pois o usuário só verá este texto final.",
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
Se as ferramentas trouxeram dados (como schemas, tabelas ou registros), E você fará o needs_tools=false, transcreva/resuma os dados no campo "explanation" formatados de forma agradável em texto puro ou markdown. O usuário NÃO VÊ os resultados das tools, a "explanation" é a única coisa que ele vai ler.

CRÍTICO — SOBRE O HISTÓRICO:
O histórico da conversa mostra interações ANTERIORES, não os dados desta execução atual.
Se o usuário pede algo como "liste tabelas", "descreva tabela X", "conte registros" ou qualquer consulta:
- SEMPRE use needs_tools=true e execute a ferramenta adequada nesta rodada
- NÃO considere respostas do histórico como dados já obtidos agora
- SOMENTE use needs_tools=false se houver um bloco "RESULTADO DE FERRAMENTA (dados reais do banco)" no contexto com os dados que respondem exatamente esta pergunta
- Nunca diga "já listei" ou "já executei" sem ter uma ferramenta executada nesta chamada

Responda APENAS o JSON, sem nenhum texto antes ou depois.
"""

    final_system_prompt = f"{system_prompt}\n\n{planning_instruction}"

    response_text = await chat_async(
        model=model,
        prompt=user_message,
        system_prompt=final_system_prompt,
        temperature=0.05,  # Muito baixo para maior determinismo em JSON
        base_url=base_url,
        api_key=api_key,
    )

    return _parse_llm_plan(response_text)


def _parse_llm_plan(raw_response: str) -> LLMPlan:
    """
    Faz parse e validação da resposta do LLM.
    Usa fallback robusto para modelos que não seguem instrução JSON exatamente.
    """
    if not raw_response or not raw_response.strip():
        logger.warning("[LLM] Resposta vazia do LLM")
        return _fallback_plan("Resposta vazia do LLM", raw_response)

    logger.debug(f"[LLM] Raw response ({len(raw_response)} chars): {raw_response[:300]}")

    # Tentar extrair JSON de markdown code block se presente
    text = raw_response.strip()
    
    # Remover markdown se presente
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)
    text = text.strip()

    # Tentar fazer parse do JSON
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Tentar encontrar JSON na resposta com regex
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
            except json.JSONDecodeError:
                logger.warning(f"LLM não retornou JSON válido: {text[:200]}")
                return _fallback_plan(text, raw_response)
        else:
            logger.warning(f"Nenhum JSON encontrado na resposta: {text[:200]}")
            return _fallback_plan(text, raw_response)

    # Validar e normalizar campos obrigatórios
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

    sql = data.get("sql")
    if sql and not isinstance(sql, str):
        sql = str(sql)
    if sql:
        sql = sql.strip()
    if not sql:
        sql = None

    explanation = data.get("explanation", "")
    if not isinstance(explanation, str):
        explanation = str(explanation)

    plan = LLMPlan(
        intent=intent,
        needs_tools=needs_tools,
        tools=tools,
        sql=sql,
        explanation=explanation,
        risk_hint=risk_hint,
    )
    logger.info(
        f"[LLM] Plano parseado | intent={intent} | needs_tools={needs_tools} "
        f"| tools={[str(t.get('name', '?')) + '.' + str(t.get('action', '?')) for t in tools]} "
        f"| risk={risk_hint} | sql_len={len(sql) if sql else 0}"
    )
    return plan


def _fallback_plan(text: str, raw: str) -> LLMPlan:
    """
    Cria um plano de fallback quando o LLM não retorna JSON válido.
    Trata a resposta como explicação informativa.
    """
    return LLMPlan(
        intent="explain",
        needs_tools=False,
        tools=[],
        sql=None,
        explanation=text,
        risk_hint="low",
    )


async def check_connection() -> tuple[bool, str]:
    """
    Verifica se Ollama está disponível.
    
    Returns:
        (available, message)
    """
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [m["name"] for m in data.get("models", [])]
                return True, f"Ollama disponível. Modelos: {', '.join(models[:5])}"
            return False, f"Ollama retornou status {response.status_code}"
    except Exception as e:
        return False, f"Ollama indisponível: {str(e)}"


async def list_models() -> list[str]:
    """Lista modelos disponíveis no Ollama."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
    except Exception:
        pass
    return []
