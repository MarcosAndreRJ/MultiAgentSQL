"""
Tipos centrais para separar os domínios de banco no sistema.
"""
from enum import Enum


class DatabaseDomain(str, Enum):
    """Domínio lógico de banco usado pela aplicação."""

    PLATFORM_DB = "platform_db"
    TARGET_DB = "target_db"


class TargetDatabaseType(str, Enum):
    """Tipos de banco suportados para target_db (futuro)."""

    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    MSSQL = "mssql"
    SQLITE = "sqlite"


class RuntimeDataMode(str, Enum):
    """Modo operacional para leitura de dados de configuração."""

    REAL_DATABASE = "real_database"
    FALLBACK = "fallback"
