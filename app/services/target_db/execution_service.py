"""
Execucao SQL para target_db (por agente).

Nesta fase mantemos apenas o contrato de retorno.
"""
from app.core.database_domains import DatabaseDomain


def execute_target_query(agent_id: str, sql: str) -> dict:
    """Contrato inicial para execucao SQL no target_db."""

    return {
        "domain": DatabaseDomain.TARGET_DB.value,
        "agent_id": agent_id,
        "sql": sql,
        "status": "not_implemented",
        "rows": [],
        "error": "Target DB execution is not implemented yet",
    }
