"""
Query Cache Service — Cache determinístico de resultados fast-path por agente.

FASE ATUAL (Digest Prime): estrutura base com TTL simples.
PREPARADO PARA EVOLUÇÃO:
  - cache de resultados COUNT por tabela (invalida on digest refresh)
  - cache de DESCRIBE TABLE (estável entre sessões)
  - invalidação seletiva (por tabela, por operação)
  - ranking de queries frequentes para pré-aquecimento
  - cache de planos LLM para queries idênticas (custo zero)

Arquivo de dados:
  data/cache/{agent_id}.query_cache.json

Formato atual:
{
  "agent_id": "...",
  "updated_at": "...",
  "entries": {
    "<cache_key>": {
      "result": {...},
      "created_at": "...",
      "ttl_seconds": 300,
      "hits": 3
    }
  }
}

Chave de cache: hash SHA-256 de (agent_id + intent + table_name).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.core.logger import get_logger
from app.core.settings import settings

logger = get_logger("query_cache_service")

# TTL padrão em segundos por intent
_DEFAULT_TTL: dict[str, int] = {
    "DESCRIBE_TABLE": 3600,      # 1 hora — schema muda raramente
    "SHOW_CREATE_TABLE": 3600,
    "COUNT_TABLE": 60,           # 1 minuto — COUNT muda frequentemente
    "LIST_TABLES": 600,          # 10 minutos
    "LIST_VIEWS": 600,
    "LIST_TRIGGERS": 600,
    "LIST_RECORDS": 30,          # 30 segundos — dados ao vivo
}
_FALLBACK_TTL = 120


# ─── Caminho ───────────────────────────────────────────────────────────────────

def _cache_path(agent_id: str) -> Path:
    return settings.cache_path / f"{agent_id}.query_cache.json"


# ─── Geração de chave ─────────────────────────────────────────────────────────

def _make_key(agent_id: str, intent: str, table: Optional[str] = None) -> str:
    """Gera chave de cache SHA-256 para um (agent, intent, table)."""
    raw = f"{agent_id}::{intent}::{(table or '').lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ─── CRUD ─────────────────────────────────────────────────────────────────────

def _load(agent_id: str) -> dict:
    path = _cache_path(agent_id)
    if not path.exists():
        return {"agent_id": agent_id, "updated_at": None, "entries": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"[CACHE] Erro ao ler cache '{agent_id}': {e}")
        return {"agent_id": agent_id, "updated_at": None, "entries": {}}


def _save(agent_id: str, data: dict) -> None:
    path = _cache_path(agent_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    try:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        logger.error(f"[CACHE] Erro ao salvar cache '{agent_id}': {e}")


# ─── API pública ──────────────────────────────────────────────────────────────

def get(agent_id: str, intent: str, table: Optional[str] = None) -> Optional[Any]:
    """
    Busca um resultado cacheado. Retorna None se não existir ou expirado.
    Incrementa contador de hits.
    """
    key = _make_key(agent_id, intent, table)
    data = _load(agent_id)
    entry = data["entries"].get(key)
    if entry is None:
        return None

    # Verificar TTL
    created = datetime.fromisoformat(entry["created_at"])
    now = datetime.now(timezone.utc)
    age = (now - created).total_seconds()
    if age > entry.get("ttl_seconds", _FALLBACK_TTL):
        # Expirado — remover silenciosamente
        data["entries"].pop(key, None)
        _save(agent_id, data)
        logger.debug(f"[CACHE] Expirado: intent={intent} table={table} age={age:.0f}s")
        return None

    # Cache hit
    entry["hits"] = entry.get("hits", 0) + 1
    _save(agent_id, data)
    logger.debug(f"[CACHE] HIT: intent={intent} table={table} hits={entry['hits']}")
    return entry["result"]


def put(
    agent_id: str,
    intent: str,
    result: Any,
    table: Optional[str] = None,
    ttl_seconds: Optional[int] = None,
) -> None:
    """
    Armazena resultado no cache.
    TTL padrão definido por intent em _DEFAULT_TTL.
    """
    key = _make_key(agent_id, intent, table)
    ttl = ttl_seconds or _DEFAULT_TTL.get(intent, _FALLBACK_TTL)
    data = _load(agent_id)
    data["entries"][key] = {
        "intent": intent,
        "table": table,
        "result": result,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "ttl_seconds": ttl,
        "hits": 0,
    }
    _save(agent_id, data)
    logger.debug(f"[CACHE] SET: intent={intent} table={table} ttl={ttl}s")


def invalidate(agent_id: str, intent: Optional[str] = None, table: Optional[str] = None) -> int:
    """
    Invalida entradas de cache.
    - Se intent e table forem None: limpa todo o cache do agente.
    - Se table for fornecida: remove todas as entradas para essa tabela.
    - Se intent for fornecida: remove todas as entradas desse intent.

    Retorna número de entradas removidas.
    """
    data = _load(agent_id)
    entries = data["entries"]

    if intent is None and table is None:
        removed = len(entries)
        data["entries"] = {}
        _save(agent_id, data)
        logger.info(f"[CACHE] Invalidado tudo para agente={agent_id}: {removed} entradas")
        return removed

    table_lower = table.lower() if table else None
    to_remove = [
        k for k, v in entries.items()
        if (intent is None or v.get("intent") == intent)
        and (table_lower is None or (v.get("table") or "").lower() == table_lower)
    ]

    for k in to_remove:
        del entries[k]
    if to_remove:
        _save(agent_id, data)
    logger.debug(f"[CACHE] Invalidadas {len(to_remove)} entradas: intent={intent} table={table}")
    return len(to_remove)


def stats(agent_id: str) -> dict:
    """Retorna estatísticas do cache (total de entradas, hits cumulativos)."""
    data = _load(agent_id)
    entries = data["entries"]
    total_hits = sum(e.get("hits", 0) for e in entries.values())
    return {
        "agent_id": agent_id,
        "entries": len(entries),
        "total_hits": total_hits,
        "updated_at": data.get("updated_at"),
    }
