"""
Tests for agent LLM binding validation and resolution services.

Covers:
- unit tests for validate_agent_llm_binding
- unit tests for resolve_agent_llm_binding
- integration test for the PUT /api/agents/{agent_id}/llm-binding endpoint returning validation errors

These tests use an in-memory SQLite database and monkeypatch platform_db_state to behave as if
the platform DB is available.
"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from app.db.session import Base
from app.db import models
from app.services.platform import agent_bindings_service
from app.services.platform import platform_db_state
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api import routes_agent_bindings


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Ensure models are registered and create tables
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_validate_agent_llm_binding_valid(db, monkeypatch):
    monkeypatch.setattr(platform_db_state, "is_platform_db_connected", lambda: True)

    p = models.LLMProvider(name="prov", provider_type="openai", is_active=True)
    db.add(p)
    db.commit()
    db.refresh(p)

    m = models.LLMModel(
        provider_id=p.id,
        model_identifier="m1",
        display_name="M1",
        supports_tools=True,
        supports_json=True,
        supports_streaming=True,
        context_window=8192,
        is_available=True,
        is_active=True,
    )
    db.add(m)
    db.commit()
    db.refresh(m)

    payload = {
        "provider_id": p.id,
        "model_id": m.id,
        "supports_tools_required": True,
        "supports_json_required": True,
        "require_streaming": True,
        "min_context_window": 4096,
    }

    res = agent_bindings_service.validate_agent_llm_binding(db, payload)
    assert res["is_valid"] is True
    assert res["errors"] == []


def test_validate_agent_llm_binding_missing_entities(db, monkeypatch):
    monkeypatch.setattr(platform_db_state, "is_platform_db_connected", lambda: True)

    payload = {"provider_id": 9999, "model_id": 9999}
    res = agent_bindings_service.validate_agent_llm_binding(db, payload)
    assert res["is_valid"] is False
    assert "provider_id does not reference an existing provider" in res["errors"]
    assert "model_id does not reference an existing model" in res["errors"]


def test_validate_agent_llm_binding_model_provider_mismatch(db, monkeypatch):
    monkeypatch.setattr(platform_db_state, "is_platform_db_connected", lambda: True)

    p1 = models.LLMProvider(name="p1", provider_type="openai", is_active=True)
    p2 = models.LLMProvider(name="p2", provider_type="openai", is_active=True)
    db.add_all([p1, p2])
    db.commit()
    db.refresh(p1)
    db.refresh(p2)

    m = models.LLMModel(provider_id=p2.id, model_identifier="m2", display_name="M2", is_available=True, is_active=True)
    db.add(m)
    db.commit()
    db.refresh(m)

    payload = {"provider_id": p1.id, "model_id": m.id}
    res = agent_bindings_service.validate_agent_llm_binding(db, payload)
    assert res["is_valid"] is False
    assert "model does not belong to the specified provider" in res["errors"]


def test_validate_agent_llm_binding_capabilities_and_fallbacks(db, monkeypatch):
    monkeypatch.setattr(platform_db_state, "is_platform_db_connected", lambda: True)

    p = models.LLMProvider(name="p", provider_type="openai", is_active=True)
    fp = models.LLMProvider(name="fp", provider_type="openai", is_active=True)
    db.add_all([p, fp])
    db.commit()
    db.refresh(p)
    db.refresh(fp)

    m = models.LLMModel(
        provider_id=p.id,
        model_identifier="m",
        display_name="M",
        supports_tools=False,
        supports_json=False,
        supports_streaming=False,
        context_window=512,
        is_available=True,
        is_active=True,
    )

    fm = models.LLMModel(
        provider_id=p.id,
        model_identifier="fm",
        display_name="FM",
        supports_tools=True,
        supports_json=True,
        supports_streaming=True,
        context_window=1024,
        is_available=True,
        is_active=True,
    )

    db.add_all([m, fm])
    db.commit()
    db.refresh(m)
    db.refresh(fm)

    payload = {
        "provider_id": p.id,
        "model_id": m.id,
        "supports_tools_required": True,
        "supports_json_required": True,
        "require_streaming": True,
        "min_context_window": 1024,
    }

    res = agent_bindings_service.validate_agent_llm_binding(db, payload)
    assert res["is_valid"] is False
    assert "model does not support tools but tools are required" in res["errors"]
    assert "model does not support json but json is required" in res["errors"]
    assert "model does not support streaming but streaming is required" in res["errors"]
    assert "model context window is smaller than the required min_context_window" in res["errors"]

    # fallback coherence mismatch: fm belongs to provider p but payload sets fallback_provider_id to fp
    payload2 = {"provider_id": p.id, "model_id": m.id, "fallback_provider_id": fp.id, "fallback_model_id": fm.id}
    res2 = agent_bindings_service.validate_agent_llm_binding(db, payload2)
    assert "fallback model does not belong to the fallback provider" in res2["errors"]


def test_resolve_agent_llm_binding_no_binding(db, monkeypatch):
    monkeypatch.setattr(platform_db_state, "is_platform_db_connected", lambda: True)
    res = agent_bindings_service.resolve_agent_llm_binding(db, "no-such-agent")
    assert res["binding"] is None
    assert res["is_valid"] is False
    assert "no binding found" in res["validation_errors"]


def test_resolve_agent_llm_binding_valid_binding(db, monkeypatch):
    monkeypatch.setattr(platform_db_state, "is_platform_db_connected", lambda: True)

    p = models.LLMProvider(name="prov", provider_type="openai", is_active=True)
    db.add(p)
    db.commit()
    db.refresh(p)

    m = models.LLMModel(
        provider_id=p.id,
        model_identifier="m1",
        display_name="M1",
        supports_tools=True,
        supports_json=True,
        supports_streaming=True,
        context_window=4096,
        is_available=True,
        is_active=True,
    )
    db.add(m)
    db.commit()
    db.refresh(m)

    b = models.AgentLLMBinding(
        agent_id="ag1",
        provider_id=p.id,
        model_id=m.id,
        is_default=True,
        fallback_order=0,
        supports_json_required=False,
        supports_tools_required=False,
        is_active=True,
    )
    db.add(b)
    db.commit()
    db.refresh(b)

    res = agent_bindings_service.resolve_agent_llm_binding(db, "ag1")
    assert res["binding"] is not None
    assert res["is_valid"] is True
    assert res["binding"].agent_id == "ag1"


def test_resolve_agent_llm_binding_invalid_model(db, monkeypatch):
    monkeypatch.setattr(platform_db_state, "is_platform_db_connected", lambda: True)

    p = models.LLMProvider(name="prov2", provider_type="openai", is_active=True)
    db.add(p)
    db.commit()
    db.refresh(p)

    m = models.LLMModel(provider_id=p.id, model_identifier="m2", display_name="M2", is_available=False, is_active=False)
    db.add(m)
    db.commit()
    db.refresh(m)

    b = models.AgentLLMBinding(
        agent_id="ag2",
        provider_id=p.id,
        model_id=m.id,
        is_default=True,
        fallback_order=0,
        supports_json_required=False,
        supports_tools_required=False,
        is_active=True,
    )
    db.add(b)
    db.commit()
    db.refresh(b)

    res = agent_bindings_service.resolve_agent_llm_binding(db, "ag2")
    assert res["binding"] is not None
    assert res["is_valid"] is False
    assert "model is not active/available" in res["validation_errors"]


def test_put_agent_llm_binding_integration_validation_error(db, monkeypatch):
    monkeypatch.setattr(platform_db_state, "is_platform_db_connected", lambda: True)

    app = FastAPI()
    app.include_router(routes_agent_bindings.router)

    def _override_get_db():
        yield db

    # override the dependency used by the routes module
    app.dependency_overrides[routes_agent_bindings.get_db] = _override_get_db
    client = TestClient(app)

    payload = {"provider_id": 9999, "model_id": 9999}
    res = client.put("/api/agents/agent-x/llm-binding", json=payload)
    assert res.status_code == 400
    data = res.json()
    assert "errors" in data["detail"]
    assert "provider_id does not reference an existing provider" in data["detail"]["errors"]
