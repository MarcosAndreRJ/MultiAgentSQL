from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes_agents


def _build_client(monkeypatch) -> TestClient:
    app = FastAPI()
    app.include_router(routes_agents.router)
    return TestClient(app)


def test_agent_query_success(monkeypatch):
    client = _build_client(monkeypatch)

    monkeypatch.setattr(
        routes_agents.query_service,
        "execute_read_query",
        lambda agent_id, raw_query: {
            "status": "success",
            "execution_id": "exec_123",
            "rows": [[1, "ok"]],
            "execution_time_ms": 12.5,
        },
    )

    res = client.post("/api/agents/ag1/query", json={"query": "SELECT 1"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["execution_id"] == "exec_123"
    assert data["rows"] == [[1, "ok"]]


def test_agent_query_validation_error(monkeypatch):
    client = _build_client(monkeypatch)

    def _raise(*args, **kwargs):
        raise ValueError("Comando não permitido")

    monkeypatch.setattr(routes_agents.query_service, "execute_read_query", _raise)

    res = client.post("/api/agents/ag1/query", json={"query": "DELETE FROM users"})
    assert res.status_code == 403
    assert "não permitido" in res.json()["detail"].lower()
