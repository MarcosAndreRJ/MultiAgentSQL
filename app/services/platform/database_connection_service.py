from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from app.db import models as db_models
from app.schemas.agent_bindings import AgentDatabaseBindingCreate
from app.utils.crypto import encrypt_secret
from app.core.logger import get_logger

logger = get_logger("services.platform.database_connection")


def create_connection(db: Session, data: dict) -> db_models.DatabaseConnection:
    # validações mínimas
    required = ("host", "db_type", "database_name", "username", "password", "name")
    for k in required:
        if not data.get(k):
            raise ValueError(f"Campo obrigatório ausente: {k}")

    # prevenir duplicidade simples
    existing = db.query(db_models.DatabaseConnection).filter(
        db_models.DatabaseConnection.host == data["host"],
        db_models.DatabaseConnection.database_name == data["database_name"],
        db_models.DatabaseConnection.username == data["username"],
    ).first()
    if existing:
        raise ValueError("Já existe uma conexão com esse host+db+user")

    encrypted = encrypt_secret(data["password"])

    row = db_models.DatabaseConnection(
        name=data.get("name"),
        db_type=data.get("db_type", "mysql"),
        host=data.get("host"),
        port=data.get("port", 3306),
        database_name=data.get("database_name"),
        username=data.get("username"),
        password_encrypted=encrypted,
        extra_config_json=data.get("extra_config_json"),
        is_active=bool(data.get("is_active", True)),
    )

    db.add(row)
    try:
        db.commit()
        db.refresh(row)
    except IntegrityError:
        db.rollback()
        raise

    logger.info(f"DatabaseConnection criada: {row.name} ({row.id})")
    return row


def list_connections(db: Session) -> List[dict]:
    rows = db.query(db_models.DatabaseConnection).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "db_type": r.db_type,
            "host": r.host,
            "port": r.port,
            "database_name": r.database_name,
            "username": r.username,
            "is_active": bool(r.is_active),
            "created_at": r.created_at,
            "updated_at": r.updated_at,
        }
        for r in rows
    ]


def get_connection(db: Session, connection_id: int) -> Optional[dict]:
    r = db.query(db_models.DatabaseConnection).filter(db_models.DatabaseConnection.id == connection_id).first()
    if not r:
        return None
    return {
        "id": r.id,
        "name": r.name,
        "db_type": r.db_type,
        "host": r.host,
        "port": r.port,
        "database_name": r.database_name,
        "username": r.username,
        "is_active": bool(r.is_active),
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }


def activate_connection(db: Session, connection_id: int) -> Optional[dict]:
    r = db.query(db_models.DatabaseConnection).filter(db_models.DatabaseConnection.id == connection_id).first()
    if not r:
        return None
    r.is_active = True
    r.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(r)
    return get_connection(db, connection_id)


def deactivate_connection(db: Session, connection_id: int) -> Optional[dict]:
    r = db.query(db_models.DatabaseConnection).filter(db_models.DatabaseConnection.id == connection_id).first()
    if not r:
        return None
    r.is_active = False
    r.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(r)
    return get_connection(db, connection_id)
