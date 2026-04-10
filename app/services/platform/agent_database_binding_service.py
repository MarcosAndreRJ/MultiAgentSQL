from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from app.db import models as db_models
from app.utils.crypto import decrypt_secret
from app.core.logger import get_logger

logger = get_logger("services.platform.agent_db_binding")


def bind_agent_to_connection(db: Session, agent_id: str, connection_id: int, is_default: bool = False, access_mode: str = "readonly", schema_scope: Optional[str] = None) -> db_models.AgentDatabaseBindingV2:
    # valida existência
    conn = db.query(db_models.DatabaseConnection).filter(db_models.DatabaseConnection.id == connection_id).first()
    if not conn:
        raise ValueError("DatabaseConnection não encontrada")

    mode = (access_mode or "readonly").lower()
    if mode not in {"readonly", "readwrite"}:
        raise ValueError("access_mode inválido. Use 'readonly' ou 'readwrite'")

    # se for default, remover flag default de outros bindings deste agente
    if is_default:
        db.query(db_models.AgentDatabaseBindingV2).filter(
            db_models.AgentDatabaseBindingV2.agent_id == agent_id,
            db_models.AgentDatabaseBindingV2.is_default == True
        ).update({"is_default": False})

    row = db_models.AgentDatabaseBindingV2(
        agent_id=agent_id,
        database_connection_id=connection_id,
        is_default=is_default,
        access_mode=mode,
        schema_scope=schema_scope,
        is_active=True,
    )
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
    except IntegrityError:
        db.rollback()
        raise

    logger.info(f"Agent '{agent_id}' vinculado à connection {connection_id} (binding id={row.id})")
    return row


def list_agent_bindings(db: Session, agent_id: str):
    rows = db.query(db_models.AgentDatabaseBindingV2).filter(db_models.AgentDatabaseBindingV2.agent_id == agent_id).all()
    results = []
    for r in rows:
        conn = db.query(db_models.DatabaseConnection).filter(db_models.DatabaseConnection.id == r.database_connection_id).first()
        results.append({
            "id": r.id,
            "agent_id": r.agent_id,
            "connection_id": r.database_connection_id,
            "connection_name": conn.name if conn else None,
            "is_default": bool(r.is_default),
            "access_mode": r.access_mode,
            "schema_scope": r.schema_scope,
            "is_active": bool(r.is_active),
            "created_at": r.created_at,
        })
    return results


def set_binding_default(db: Session, binding_id: int):
    b = db.query(db_models.AgentDatabaseBindingV2).filter(db_models.AgentDatabaseBindingV2.id == binding_id).first()
    if not b:
        return None
    # limpar outros defaults
    db.query(db_models.AgentDatabaseBindingV2).filter(
        db_models.AgentDatabaseBindingV2.agent_id == b.agent_id,
        db_models.AgentDatabaseBindingV2.id != binding_id
    ).update({"is_default": False})
    b.is_default = True
    b.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(b)
    return b


def activate_binding(db: Session, binding_id: int):
    b = db.query(db_models.AgentDatabaseBindingV2).filter(db_models.AgentDatabaseBindingV2.id == binding_id).first()
    if not b:
        return None
    b.is_active = True
    b.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(b)
    return b


def deactivate_binding(db: Session, binding_id: int):
    b = db.query(db_models.AgentDatabaseBindingV2).filter(db_models.AgentDatabaseBindingV2.id == binding_id).first()
    if not b:
        return None
    b.is_active = False
    b.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(b)
    return b


def resolve_agent_database_binding(
    db: Session,
    agent_id: str,
    database_connection_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Resolve o binding ativo de banco para um agente.

    Regras:
    - busca somente bindings ativos (v2)
    - prioriza `is_default = True`
    - fallback: primeiro ativo
    - exige `DatabaseConnection` ativa
    - erro controlado quando não houver binding válido

    Retorna um dicionário canônico para uso no connection manager/executor,
    contendo credenciais já decriptadas apenas em memória de runtime.
    """
    q = db.query(db_models.AgentDatabaseBindingV2).filter(
        db_models.AgentDatabaseBindingV2.agent_id == agent_id,
        db_models.AgentDatabaseBindingV2.is_active == True,
    )

    if database_connection_id is not None:
        q = q.filter(db_models.AgentDatabaseBindingV2.database_connection_id == database_connection_id)

    candidates = q.order_by(
        db_models.AgentDatabaseBindingV2.is_default.desc(),
        db_models.AgentDatabaseBindingV2.created_at.asc(),
        db_models.AgentDatabaseBindingV2.id.asc(),
    ).all()

    if not candidates:
        raise ValueError(f"No active database binding found for agent '{agent_id}'")

    for binding in candidates:
        conn = db.query(db_models.DatabaseConnection).filter(
            db_models.DatabaseConnection.id == binding.database_connection_id,
            db_models.DatabaseConnection.is_active == True,
        ).first()

        if conn is None:
            continue

        try:
            decrypted_password = decrypt_secret(conn.password_encrypted)
        except Exception:
            logger.error(
                "Failed to decrypt database connection password | agent=%s | db_connection_id=%s",
                agent_id,
                binding.database_connection_id,
            )
            raise ValueError("Database connection credentials are invalid")

        return {
            "source": "agent_database_bindings_v2",
            "agent_id": binding.agent_id,
            "binding_id": binding.id,
            "database_connection_id": binding.database_connection_id,
            "is_default": bool(binding.is_default),
            "access_mode": binding.access_mode or "readonly",
            "schema_scope": binding.schema_scope,
            "binding_updated_at": binding.updated_at,
            "db_type": conn.db_type,
            "host": conn.host,
            "port": conn.port,
            "database_name": conn.database_name,
            "username": conn.username,
            "password": decrypted_password,
            "connection_updated_at": conn.updated_at,
        }

    raise ValueError(f"No active database connection available for agent '{agent_id}'")
