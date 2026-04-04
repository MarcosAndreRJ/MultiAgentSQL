"""
Estado de conectividade do platform_db.

Este modulo cria um ponto central para diferenciar operacao
com banco real vs fallback, sem alterar a logica existente.
"""
from sqlalchemy import text

from app.core.database_domains import RuntimeDataMode
from app.db.session import SessionLocal


def is_platform_db_connected() -> bool:
    """Retorna True quando o platform_db responde a uma query real."""

    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        db.close()


def get_platform_data_mode() -> RuntimeDataMode:
    """Retorna o modo atual: real_database ou fallback."""

    return RuntimeDataMode.REAL_DATABASE if is_platform_db_connected() else RuntimeDataMode.FALLBACK
