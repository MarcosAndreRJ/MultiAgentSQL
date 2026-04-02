"""
Database Connection Manager: gerencia conexões MySQL por agente.
Cada agente tem sua própria conexão isolada.
"""
import time
from typing import Optional

import mysql.connector
from mysql.connector import Error as MySQLError

from app.core.logger import get_logger
from app.schemas.agent import DatabaseConfig

logger = get_logger("db_connection_manager")

# Pool de conexões por agente: {agent_id: connection}
_connections: dict[str, mysql.connector.MySQLConnection] = {}


def get_connection(agent_id: str, db_config: DatabaseConfig) -> mysql.connector.MySQLConnection:
    """
    Retorna uma conexão MySQL ativa para o agente.
    Reconecta automaticamente se a conexão estiver inativa.
    
    Args:
        agent_id: ID do agente (usado como chave de cache).
        db_config: Configuração de banco de dados do agente.
        
    Returns:
        Conexão MySQL ativa.
        
    Raises:
        MySQLError: Se não conseguir conectar.
    """
    conn = _connections.get(agent_id)

    # Verificar se a conexão está ativa
    if conn is not None:
        try:
            conn.ping(reconnect=True, attempts=2, delay=1)
            return conn
        except MySQLError:
            logger.warning(f"Conexão inativa para agente '{agent_id}', reconectando...")
            _connections.pop(agent_id, None)

    # Criar nova conexão
    conn = _create_connection(agent_id, db_config)
    _connections[agent_id] = conn
    return conn


def _create_connection(agent_id: str, db_config: DatabaseConfig) -> mysql.connector.MySQLConnection:
    """Cria uma nova conexão MySQL."""
    logger.info(f"Conectando ao MySQL | agente={agent_id} | host={db_config.host} | db={db_config.name}")
    
    try:
        conn = mysql.connector.connect(
            host=db_config.host,
            port=db_config.port,
            database=db_config.name,
            user=db_config.user,
            password=db_config.password,
            connect_timeout=db_config.connect_timeout,
            # Usar prepared statements e charset correto
            charset="utf8mb4",
            use_unicode=True,
            # Autocommit desligado por padrão para controle
            autocommit=True,
            # Habilitar multi-statements (necessário para procedures/triggers)
            # Controlado por flag na execução
        )
        logger.info(f"Conexão estabelecida | agente={agent_id} | db={db_config.name}")
        return conn
    except MySQLError as e:
        logger.error(f"Falha na conexão | agente={agent_id} | erro={e}")
        raise


def test_connection(db_config: DatabaseConfig) -> tuple[bool, str]:
    """
    Testa uma conexão MySQL.
    
    Returns:
        (success, message)
    """
    try:
        conn = mysql.connector.connect(
            host=db_config.host,
            port=db_config.port,
            database=db_config.name,
            user=db_config.user,
            password=db_config.password,
            connect_timeout=db_config.connect_timeout,
            charset="utf8mb4",
        )
        
        # Verificar versão
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return True, f"Conectado com sucesso | MySQL {version[0]} | db={db_config.name}"
    except MySQLError as e:
        return False, f"Falha na conexão: {str(e)}"


def close_connection(agent_id: str) -> None:
    """Fecha e remove a conexão de um agente."""
    conn = _connections.pop(agent_id, None)
    if conn:
        try:
            conn.close()
            logger.info(f"Conexão fechada | agente={agent_id}")
        except Exception:
            pass


def close_all() -> None:
    """Fecha todas as conexões (usado no shutdown)."""
    for agent_id in list(_connections.keys()):
        close_connection(agent_id)
    logger.info("Todas as conexões MySQL fechadas")
