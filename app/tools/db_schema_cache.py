"""
db_schema_cache: Cache de schema para reduzir introspecção repetitiva.
Armazena resultados recentes de introspecção por agente.
"""
import time
from typing import Optional

from app.core.logger import get_logger

logger = get_logger("db_schema_cache")

# Cache: {agent_id: {cache_key: {data, expires_at}}}
_cache: dict[str, dict] = {}

# TTL padrão do cache em segundos (5 minutos)
DEFAULT_TTL = 300


def get(agent_id: str, cache_key: str) -> Optional[list]:
    """
    Busca dados no cache.
    
    Returns:
        Dados cacheados ou None se não existir/expirado.
    """
    agent_cache = _cache.get(agent_id, {})
    entry = agent_cache.get(cache_key)
    if not entry:
        return None

    if time.time() > entry["expires_at"]:
        # Expirado, remover
        agent_cache.pop(cache_key, None)
        logger.debug(f"Cache expirado | agente={agent_id} | chave={cache_key}")
        return None

    logger.debug(f"Cache hit | agente={agent_id} | chave={cache_key}")
    return entry["data"]


def set(agent_id: str, cache_key: str, data: list, ttl: int = DEFAULT_TTL) -> None:
    """Armazena dados no cache."""
    if agent_id not in _cache:
        _cache[agent_id] = {}

    _cache[agent_id][cache_key] = {
        "data": data,
        "expires_at": time.time() + ttl,
    }
    logger.debug(f"Cache set | agente={agent_id} | chave={cache_key} | ttl={ttl}s")


def invalidate(agent_id: str, cache_key: Optional[str] = None) -> None:
    """
    Invalida cache de um agente.
    Se cache_key for None, invalida todo o cache do agente.
    """
    if agent_id not in _cache:
        return

    if cache_key:
        _cache[agent_id].pop(cache_key, None)
        logger.debug(f"Cache invalidado | agente={agent_id} | chave={cache_key}")
    else:
        _cache[agent_id] = {}
        logger.debug(f"Cache limpo | agente={agent_id}")


def invalidate_all() -> None:
    """Invalida todo o cache."""
    _cache.clear()
    logger.info("Cache de schema limpo completamente")


# Chaves de cache pré-definidas
CACHE_TABLES = "list_tables"
CACHE_VIEWS = "list_views"
CACHE_TRIGGERS = "list_triggers"
CACHE_PROCEDURES = "list_procedures"
CACHE_FUNCTIONS = "list_functions"


def table_key(table_name: str) -> str:
    """Chave de cache para descrição de uma tabela."""
    return f"describe:{table_name}"


def create_key(obj_type: str, name: str) -> str:
    """Chave de cache para DDL de um objeto."""
    return f"create:{obj_type}:{name}"
