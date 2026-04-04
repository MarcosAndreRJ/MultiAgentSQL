"""
Health dedicado ao target_db por agente.
"""
from app.core.database_domains import DatabaseDomain


def get_target_db_health(agent_id: str) -> dict:
    """Estrutura base de health de target_db por agente."""

    return {
        "domain": DatabaseDomain.TARGET_DB.value,
        "agent_id": agent_id,
        "connected": False,
        "status": "not_implemented",
        "message": "Target DB connection is not implemented yet",
    }
