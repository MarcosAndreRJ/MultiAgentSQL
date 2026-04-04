from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.db import models
from app.services.platform.agent_database_binding_service import resolve_agent_database_binding
from app.utils.crypto import encrypt_secret


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()


def _create_connection(db, name: str, is_active: bool = True):
    row = models.DatabaseConnection(
        name=name,
        db_type="mysql",
        host="127.0.0.1",
        port=3306,
        database_name=f"db_{name}",
        username="user",
        password_encrypted=encrypt_secret("secret"),
        is_active=is_active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_resolve_prefers_default_binding(db_session):
    c1 = _create_connection(db_session, "a")
    c2 = _create_connection(db_session, "b")

    b1 = models.AgentDatabaseBindingV2(
        agent_id="agent-1",
        database_connection_id=c1.id,
        is_default=False,
        access_mode="readonly",
        is_active=True,
    )
    b2 = models.AgentDatabaseBindingV2(
        agent_id="agent-1",
        database_connection_id=c2.id,
        is_default=True,
        access_mode="readonly",
        is_active=True,
    )
    db_session.add_all([b1, b2])
    db_session.commit()

    resolved = resolve_agent_database_binding(db_session, "agent-1")
    assert resolved["database_connection_id"] == c2.id
    assert resolved["is_default"] is True


def test_resolve_fallback_first_active_when_no_default(db_session):
    c1 = _create_connection(db_session, "first")
    c2 = _create_connection(db_session, "second")

    b1 = models.AgentDatabaseBindingV2(
        agent_id="agent-2",
        database_connection_id=c1.id,
        is_default=False,
        access_mode="readonly",
        is_active=True,
    )
    b2 = models.AgentDatabaseBindingV2(
        agent_id="agent-2",
        database_connection_id=c2.id,
        is_default=False,
        access_mode="readonly",
        is_active=True,
    )
    db_session.add_all([b1, b2])
    db_session.commit()

    resolved = resolve_agent_database_binding(db_session, "agent-2")
    assert resolved["database_connection_id"] == c1.id


def test_resolve_skips_inactive_connections(db_session):
    c1 = _create_connection(db_session, "inactive", is_active=False)
    c2 = _create_connection(db_session, "active", is_active=True)

    b1 = models.AgentDatabaseBindingV2(
        agent_id="agent-3",
        database_connection_id=c1.id,
        is_default=True,
        access_mode="readonly",
        is_active=True,
    )
    b2 = models.AgentDatabaseBindingV2(
        agent_id="agent-3",
        database_connection_id=c2.id,
        is_default=False,
        access_mode="readonly",
        is_active=True,
    )
    db_session.add_all([b1, b2])
    db_session.commit()

    resolved = resolve_agent_database_binding(db_session, "agent-3")
    assert resolved["database_connection_id"] == c2.id


def test_resolve_raises_when_no_binding(db_session):
    with pytest.raises(ValueError):
        resolve_agent_database_binding(db_session, "ghost-agent")
