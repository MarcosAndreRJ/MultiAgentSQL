"""
Testes para rotas /api/diagram.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes_diagram
from app.schemas.diagram import DiagramPayload, DiagramStatus, DiagramSummary
from app.services.diagram_service import DiagramDigestInvalidError, DiagramDigestNotFoundError


def _build_client(monkeypatch) -> TestClient:
    app = FastAPI()
    app.include_router(routes_diagram.router)

    class _Agent:
        def __init__(self):
            self.name = "Agent X"

    monkeypatch.setattr(routes_diagram.agent_registry, "get", lambda agent_id: _Agent())
    return TestClient(app)


def test_get_diagram_success(monkeypatch):
    client = _build_client(monkeypatch)

    payload = DiagramPayload(
        agent_id="ag1",
        agent_name="Agent X",
        database="db1",
        generated_at="2026-03-24T00:00:00Z",
        summary=DiagramSummary(nodes=1, edges=0),
        nodes=[],
        edges=[],
    )
    monkeypatch.setattr(routes_diagram.diagram_service, "build_diagram", lambda agent_id, agent_name=None: payload)

    res = client.get("/api/diagram/ag1")
    assert res.status_code == 200
    data = res.json()
    assert data["agent_id"] == "ag1"
    assert data["database"] == "db1"
    assert data["summary"]["nodes"] == 1


def test_get_diagram_status_success(monkeypatch):
    client = _build_client(monkeypatch)
    status = DiagramStatus(agent_id="ag1", agent_name="Agent X", exists=True, valid=True, nodes=5, edges=2)
    monkeypatch.setattr(routes_diagram.diagram_service, "get_diagram_status", lambda agent_id, agent_name=None: status)

    res = client.get("/api/diagram/ag1/status")
    assert res.status_code == 200
    data = res.json()
    assert data["exists"] is True
    assert data["valid"] is True
    assert data["nodes"] == 5


def test_get_diagram_missing_digest(monkeypatch):
    client = _build_client(monkeypatch)

    def _raise_not_found(agent_id, agent_name=None):
        raise DiagramDigestNotFoundError("missing")

    monkeypatch.setattr(routes_diagram.diagram_service, "build_diagram", _raise_not_found)

    res = client.get("/api/diagram/ag1")
    assert res.status_code == 404
    assert "digest" in res.json()["detail"].lower()


def test_get_diagram_invalid_digest(monkeypatch):
    client = _build_client(monkeypatch)

    def _raise_invalid(agent_id, agent_name=None):
        raise DiagramDigestInvalidError("invalid")

    monkeypatch.setattr(routes_diagram.diagram_service, "build_diagram", _raise_invalid)

    res = client.get("/api/diagram/ag1")
    assert res.status_code == 422
    assert "invalido" in res.json()["detail"].lower()


def test_get_diagram_agent_not_found(monkeypatch):
    app = FastAPI()
    app.include_router(routes_diagram.router)
    monkeypatch.setattr(routes_diagram.agent_registry, "get", lambda agent_id: None)
    client = TestClient(app)

    res = client.get("/api/diagram/ghost")
    assert res.status_code == 404
    assert "nao encontrado" in res.json()["detail"].lower()
