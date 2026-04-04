import time
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from typing import List

from app.db import models as db_models
from app.schemas.health import HealthStatus, HealthDomain, TargetDbHealthRead
from app.utils.crypto import decrypt_secret
from app.core.logger import get_logger
from app.services.observability.execution_observability_service import generate_execution_id

logger = get_logger("observability.target_db")

def get_all_target_dbs_health(db: Session) -> List[TargetDbHealthRead]:
    """Testa a conexão física de cada target_db configurado."""
    connections = db.query(db_models.DatabaseConnection).filter(db_models.DatabaseConnection.is_active == True).all()
    results = []

    for conn in connections:
        execution_id = generate_execution_id()
        status = HealthStatus.HEALTHY
        latency = 0.0
        message = "Conexão Operacional"
        
        try:
            # 1. Decriptar senha
            password = decrypt_secret(conn.password_encrypted)
            
            # 2. Montar URL de conexão (MySQL por padrão para esta etapa)
            # engine = create_engine(f"mysql+mysqlconnector://{conn.username}:{password}@{conn.host}:{conn.port}/{conn.database_name}")
            db_url = f"mysql+mysqlconnector://{conn.username}:{password}@{conn.host}:{conn.port}/{conn.database_name}"
            
            # 3. Teste físico com Timeout Curto
            start_time = time.time()
            engine = create_engine(db_url, connect_args={"connect_timeout": 5})
            with engine.connect() as probe:
                probe.execute(text("SELECT 1"))
            latency = (time.time() - start_time) * 1000
            engine.dispose()
            
        except SQLAlchemyError as exc:
            status = HealthStatus.OFFLINE
            message = f"Falha de conexão: {str(exc)}"
            latency = -1
        except Exception as e:
            status = HealthStatus.OFFLINE
            message = f"Falha interna no check: {str(e)}"
            latency = -1

        # Log estruturado
        logger.info(
            "OBSERVABILITY | execution_id=%s | DOMAIN=%s | ENTITY=%s/%s | STATUS=%s | LATENCY=%sms",
            execution_id,
            HealthDomain.TARGET_DB,
            conn.id,
            conn.name,
            status,
            latency,
        )
        
        # Persiste histórico
        _log_health(db, conn, status, latency, message, execution_id=execution_id)

        results.append(TargetDbHealthRead(
            status=status,
            latency_ms=round(latency, 2),
            message=message,
            domain=HealthDomain.TARGET_DB,
            entity_id=str(conn.id),
            entity_name=conn.name,
            db_type=conn.db_type,
            host=conn.host
        ))

    return results

def _log_health(db: Session, conn: db_models.DatabaseConnection, status: HealthStatus, latency: float, message: str, execution_id: str | None = None):
    """Persiste o resultado do check na tabela histórica."""
    try:
        log = db_models.HealthCheckLog(
            domain=HealthDomain.TARGET_DB,
            entity_id=str(conn.id),
            entity_name=conn.name,
            status=status,
            latency_ms=int(latency),
            message=message[:255] if message else None,
            execution_id=execution_id,
            checked_at=datetime.utcnow()
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Não foi possível persistir health log para target_db {conn.id}: {e}")
