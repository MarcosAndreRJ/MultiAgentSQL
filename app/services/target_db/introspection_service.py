"""
Serviço de Introspecção de Target DB.
Permite ao agente "enxergar" o banco operacional.
"""
from typing import List, Dict
from sqlalchemy import text
from app.db.session import SessionLocal
from app.services.target_db.connection_manager import connection_manager as target_db_manager
from app.core.logger import get_logger

logger = get_logger("target_db.introspection")

def list_tables(agent_id: str) -> List[str]:
    """
    Lista todas as tabelas acessíveis no target_db do agente.
    """
    db = SessionLocal()
    try:
        engine = target_db_manager.get_engine(db, agent_id)
        with engine.connect() as conn:
            # MySQL-specific (pode ser generalizado no futuro via Inspector)
            result = conn.execute(text("SHOW TABLES"))
            return [row[0] for row in result]
    finally:
        db.close()

def describe_table(agent_id: str, table_name: str) -> Dict:
    """
    Retorna a estrutura detalhada de uma tabela (Colunas, Tipos, etc).
    Retorno padronizado conforme especificação da Etapa 3.
    """
    db = SessionLocal()
    try:
        engine = target_db_manager.get_engine(db, agent_id)
        with engine.connect() as conn:
            # DESCRIBE retorna: Field, Type, Null, Key, Default, Extra
            result = conn.execute(text(f"DESCRIBE `{table_name}`"))
            
            columns = []
            for row in result:
                columns.append({
                    "name": row[0],
                    "type": row[1],
                    "nullable": row[2] == "YES",
                    "key": row[3],
                    "default": row[4],
                    "extra": row[5]
                })
                
            return {
                "table": table_name,
                "agent_id": agent_id,
                "columns": columns
            }
    finally:
        db.close()
