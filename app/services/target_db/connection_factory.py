"""
Factory de Engines para Target DB.
Responsável por criar engines SQLAlchemy de forma isolada e segura.
"""
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from typing import Any

from app.utils.crypto import decrypt_secret
from app.core.logger import get_logger

logger = get_logger("target_db.factory")

def _get_value(binding: Any, field: str, default: Any = None) -> Any:
    if isinstance(binding, dict):
        return binding.get(field, default)
    return getattr(binding, field, default)


def create_target_engine(binding: Any, timeout: int = 5) -> Engine:
    """
    Cria uma engine SQLAlchemy dinâmica para o banco operacional do agente.
    Suporta apenas MySQL nesta fase.
    
    Args:
        binding: Objeto de binding do platform_db.
        timeout: Tempo de timeout em segundos.
        
    Returns:
        SQLAlchemy Engine pronta para uso.
    """
    db_type = (_get_value(binding, "db_type") or "").lower()
    if db_type != "mysql":
        raise ValueError(f"Tipo de banco '{db_type}' não suportado na Etapa 3.")

    username = _get_value(binding, "username")
    password = _get_value(binding, "password")
    host = _get_value(binding, "host")
    port = _get_value(binding, "port")
    database_name = _get_value(binding, "database_name")
    agent_id = _get_value(binding, "agent_id", "unknown")
    db_connection_id = _get_value(binding, "database_connection_id")

    # Compatibilidade: se vier conexão sem senha decriptada, tenta decrypt local.
    if not password and _get_value(binding, "password_encrypted"):
        password = decrypt_secret(_get_value(binding, "password_encrypted"))

    # Monta connection string (Formato: mysql+mysqlconnector://user:pass@host:port/db)
    # IMPORTANTE: Senha é tratada como segredo e não logada.
    connection_uri = (
        f"mysql+mysqlconnector://{username}:{password}@"
        f"{host}:{port}/{database_name}"
    )

    try:
        # Configurações de performance e segurança
        engine = create_engine(
            connection_uri,
            pool_pre_ping=True,      # Verifica se conexão caiu antes de usar
            pool_recycle=300,        # Recicla a cada 5min
            connect_args={
                "connect_timeout": timeout
            },
            # Esconde a URL real nos logs para não vazar a senha se o log do SQLAlchemy estiver em INFO
            hide_parameters=True 
        )
        
        logger.info(
            "Engine TargetDB criada | agent=%s | db_connection_id=%s | host=%s",
            agent_id,
            db_connection_id,
            host,
        )
        return engine
        
    except SQLAlchemyError as e:
        logger.error(
            "Falha ao criar engine de target DB | agent=%s | db_connection_id=%s | error=%s",
            agent_id,
            db_connection_id,
            str(e),
        )
        raise
