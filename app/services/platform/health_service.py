"""
Health dedicado ao platform_db.
"""
from app.core.database_domains import DatabaseDomain
from app.services.platform.platform_db_state import get_platform_data_mode, is_platform_db_connected


def get_platform_db_health() -> dict:
    """Estrutura base de health para o banco da plataforma."""

    connected = is_platform_db_connected()
    return {
        "domain": DatabaseDomain.PLATFORM_DB.value,
        "connected": connected,
        "mode": get_platform_data_mode().value,
    }
