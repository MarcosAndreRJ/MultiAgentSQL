"""
Fast-Path Intent Router: Camada determinística (Zero LLM) para resolver queries simples.
Reduz latência e sobrecarga do LLM para operações como COUNT, DESCRIBE e LIST TABLES.
"""
import re
from enum import Enum
from typing import Optional
from pydantic import BaseModel
from app.core.logger import get_logger

logger = get_logger("fast_path_router")

class FastPathIntentType(str, Enum):
    COUNT_TABLE = "COUNT_TABLE"
    LIST_TABLES = "LIST_TABLES"
    DESCRIBE_TABLE = "DESCRIBE_TABLE"
    SHOW_CREATE_TABLE = "SHOW_CREATE_TABLE"
    LIST_VIEWS = "LIST_VIEWS"
    LIST_TRIGGERS = "LIST_TRIGGERS"
    NONE = "NONE"

class FastPathIntentResult(BaseModel):
    matched: bool
    intent: FastPathIntentType
    table_name: Optional[str] = None
    confidence: float = 0.0


def _is_destructive(text: str) -> bool:
    """Impede que operações fast-path acionem comandos destrutivos acidentalmente."""
    destructive_keywords = {"delete", "drop", "update", "insert", "alter", "create", "truncate"}
    words = set(re.findall(r'\b\w+\b', text.lower()))
    
    if destructive_keywords & words:
        # Exceção para "show create" não bloquear o SHOW_CREATE_TABLE
        if "show create" in text.lower():
            # Se a única palavra destrutiva for 'create', permite
            intersect = destructive_keywords & words
            if intersect == {"create"}:
                return False
        return True
    return False


def detect_fast_path_intent(message: str) -> FastPathIntentResult:
    """
    Analisa a mensagem do usuário para detectar intents simples.
    Retorna FastPathIntentResult indicando se deve usar fast-path.
    """
    text = message.strip().lower()
    
    # Remover pontuação no final para facilitar regex (como ?, ! ou .)
    text_clean = re.sub(r'[?!.]+$', '', text).strip()

    # Se contém possíveis comandos destrutivos, cai fora do fast-path para segurança total
    if _is_destructive(text_clean):
        logger.debug("[FAST_PATH] Palavra destrutiva detectada, caindo para LLM.")
        return FastPathIntentResult(matched=False, intent=FastPathIntentType.NONE)

    # 1. LIST_TABLES
    if re.search(r'^(?:list[ea]?r?\s+as\s+tabelas|mostrar\s+tabelas|quais\s+(?:as\s+)?tabelas\s+existem|list\s+tables|listar\s+tabelas)$', text_clean):
        return FastPathIntentResult(matched=True, intent=FastPathIntentType.LIST_TABLES, confidence=0.95)

    # 2. LIST_VIEWS
    if re.search(r'^(?:list[ea]?r?\s+as\s+views|mostrar\s+views|quais\s+(?:as\s+)?views\s+existem|list\s+views|listar\s+views)$', text_clean):
        return FastPathIntentResult(matched=True, intent=FastPathIntentType.LIST_VIEWS, confidence=0.95)

    # 3. LIST_TRIGGERS (e procedures)
    if re.search(r'^(?:list[ea]?r?\s+as\s+(?:triggers|procedures|functions)|quais\s+(?:as\s+)?(?:triggers|procedures|functions)\s+existem|listar\s+(?:triggers|procedures|functions))$', text_clean):
        return FastPathIntentResult(matched=True, intent=FastPathIntentType.LIST_TRIGGERS, confidence=0.95)

    # Extraidor genérico para pegar o final da frase como nome de tabela
    # Suporta: tabela X, tbl X, table X, `X`, 'X', "X", ```X```
    table_regex = r'(?:```|`|"|\')?([a-zA-Z0-9_]+)(?:```|`|"|\')?'

    # 4. COUNT_TABLE
    # Exemplos: "quantos registros tem na tabela X", "count da tabela X", "quantos itens existem em X"
    m_count = re.search(rf'(?:quantos\s+(?:registros|itens)|count)(?:\s+(?:tem|existem))?(?:\s+(?:na\s+tabela|da\s+tabela|em|de|na|da|a\s+tabela|tabela|tbl|table))?\s+{table_regex}$', text_clean)
    if m_count:
        table = m_count.group(1)
        if table not in ('tabela', 'registros', 'itens', 'banco', 'database', 'o', 'a', 'banco'):
            return FastPathIntentResult(matched=True, intent=FastPathIntentType.COUNT_TABLE, table_name=table, confidence=0.9)
            
    # Expressão flexível pro INÍCIO e extração do fim para COUNT (Ex: "me diga quantos registros existem em transacao")
    m_count2 = re.search(rf'.*(?:quantos\s+(?:registros|itens)|count).*(?:em|na|tabela|de|tbl|table)\s+{table_regex}$', text_clean)
    if m_count2:
        table = m_count2.group(1)
        if table not in ('tabela', 'registros', 'itens'):
            return FastPathIntentResult(matched=True, intent=FastPathIntentType.COUNT_TABLE, table_name=table, confidence=0.8)

    # 5. DESCRIBE_TABLE
    # Exemplos: "descreva a tabela X", "estrutura da tabela X", "show columns from X"
    m_desc = re.search(rf'(?:descrev[ea]\s+(?:a\s+)?tabela|estrutura\s+da\s+tabela|show\s+columns\s+(?:from|in)|colunas\s+da\s+tabela|describe(?: table)?)\s+{table_regex}$', text_clean)
    if m_desc:
        table = m_desc.group(1)
        if table not in ('tabela', 'estrutura', 'colunas'):
            return FastPathIntentResult(matched=True, intent=FastPathIntentType.DESCRIBE_TABLE, table_name=table, confidence=0.9)
            
    m_desc2 = re.search(rf'.*(?:estrutura|colunas).*(?:da tabela|de|tbl|table)\s+{table_regex}$', text_clean)
    if m_desc2:
        table = m_desc2.group(1)
        if table not in ('tabela', 'estrutura', 'colunas'):
            return FastPathIntentResult(matched=True, intent=FastPathIntentType.DESCRIBE_TABLE, table_name=table, confidence=0.8)

    # 6. SHOW_CREATE_TABLE
    # Exemplos: "show create table X", "ddl da tabela X", "criação da tabela X"
    m_ddl = re.search(rf'(?:(?:me\s+mostra\s+o\s+)?ddl\s+da\s+tabela|show\s+create\s+table|cria[çc][aã]o\s+da\s+tabela|script\s+da\s+tabela|c[óo]digo\s+da\s+tabela)\s+{table_regex}$', text_clean)
    if m_ddl:
        table = m_ddl.group(1)
        if table not in ('tabela', 'ddl', 'script'):
            return FastPathIntentResult(matched=True, intent=FastPathIntentType.SHOW_CREATE_TABLE, table_name=table, confidence=0.9)

    return FastPathIntentResult(matched=False, intent=FastPathIntentType.NONE, confidence=0.0)
