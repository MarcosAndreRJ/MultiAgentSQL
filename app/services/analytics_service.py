"""
Analytics Service — Coleta e persiste métricas de uso por agente.

FASE ATUAL (Digest Prime): estrutura base com registro simples.
PREPARADO PARA EVOLUÇÃO:
  - ranking de tabelas por frequência de menção
  - aliases mais utilizados (aprendizado)
  - intents fast-path mais acionados
  - distribuição de resoluções via LLM vs fast-path

Arquivo de dados:
  data/analytics/{agent_id}.usage.json

Formato atual:
{
  "agent_id": "...",
  "updated_at": "...",
  "tables_mentioned": {"Dica": 12, "Projeto": 5},
  "aliases_used": {"@Dicas": 9, "@TblDicas": 3},
  "intents": {"COUNT_TABLE": 4, "DESCRIBE_TABLE": 2, "LLM_FALLBACK": 15}
}
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.core.logger import get_logger
from app.core.settings import settings

logger = get_logger("analytics_service")


# ─── Caminho ───────────────────────────────────────────────────────────────────

def _usage_path(agent_id: str) -> Path:
    return settings.analytics_path / f"{agent_id}.usage.json"


# ─── CRUD base ────────────────────────────────────────────────────────────────

def load_usage(agent_id: str) -> dict:
    """Carrega métricas atuais. Retorna estrutura vazia se não existir."""
    path = _usage_path(agent_id)
    if not path.exists():
        return _empty(agent_id)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"[ANALYTICS] Erro ao ler métricas '{agent_id}': {e}")
        return _empty(agent_id)


def _empty(agent_id: str) -> dict:
    return {
        "agent_id": agent_id,
        "updated_at": None,
        "tables_mentioned": {},
        "aliases_used": {},
        "intents": {},
    }


def _save(agent_id: str, data: dict) -> None:
    path = _usage_path(agent_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    try:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        logger.error(f"[ANALYTICS] Erro ao salvar métricas '{agent_id}': {e}")


# ─── Registro de eventos ──────────────────────────────────────────────────────

def record_tables_mentioned(agent_id: str, tables: list[str]) -> None:
    """
    Incrementa contadores para cada tabela mencionada.
    Useful para ranking futuro de tabelas mais relevantes por agente.
    """
    if not tables:
        return
    data = load_usage(agent_id)
    for table in tables:
        data["tables_mentioned"][table] = data["tables_mentioned"].get(table, 0) + 1
    _save(agent_id, data)
    logger.debug(f"[ANALYTICS] Tabelas registradas: {tables} | agente={agent_id}")


def record_aliases_used(agent_id: str, alias_hits: dict[str, str]) -> None:
    """
    Incrementa contadores para aliases usados na mensagem.
    Futuro: base para aprendizado e sugestões de novos aliases.

    Args:
        alias_hits: {token → nome_real}, ex: {"@Dicas": "Dica"}
    """
    if not alias_hits:
        return
    data = load_usage(agent_id)
    for token in alias_hits:
        data["aliases_used"][token] = data["aliases_used"].get(token, 0) + 1
    _save(agent_id, data)
    logger.debug(f"[ANALYTICS] Aliases registrados: {list(alias_hits)} | agente={agent_id}")


def record_intent(agent_id: str, intent: str) -> None:
    """
    Registra qual intent foi acionado (fast-path ou LLM_FALLBACK).
    Futuro: otimizar heurísticas do fast-path com base em dados reais.
    """
    if not intent:
        return
    data = load_usage(agent_id)
    data["intents"][intent] = data["intents"].get(intent, 0) + 1
    _save(agent_id, data)


# ─── Consultas ────────────────────────────────────────────────────────────────

def top_tables(agent_id: str, n: int = 10) -> list[dict]:
    """
    Retorna as N tabelas mais mencionadas, ordenadas por frequência.
    Útil para: digest seletivo, sugestões proativas, ranking de contexto.
    """
    data = load_usage(agent_id)
    sorted_items = sorted(
        data["tables_mentioned"].items(),
        key=lambda x: x[1],
        reverse=True,
    )
    return [{"table": t, "count": c} for t, c in sorted_items[:n]]


def top_aliases(agent_id: str, n: int = 10) -> list[dict]:
    """
    Retorna os N aliases mais usados.
    Futuro: pré-popular sugestões com os mais usados primeiro.
    """
    data = load_usage(agent_id)
    sorted_items = sorted(
        data["aliases_used"].items(),
        key=lambda x: x[1],
        reverse=True,
    )
    return [{"alias": a, "count": c} for a, c in sorted_items[:n]]
