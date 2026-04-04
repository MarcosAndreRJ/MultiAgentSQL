"""
Servicos de schema para target_db (por agente).
"""
from app.core.database_domains import DatabaseDomain


def get_target_db_schema(agent_id: str) -> dict:
    """Resposta base para schema de target_db por agente."""

    return {
        "domain": DatabaseDomain.TARGET_DB.value,
        "agent_id": agent_id,
        "status": "not_implemented",
        "schema": None,
    }
