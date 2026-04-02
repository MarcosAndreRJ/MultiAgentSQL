"""
Tests: Pending Actions
"""
import pytest
from datetime import datetime
from app.core import pending_actions as pa


def setup_function():
    """Limpar store antes de cada teste."""
    pa._store.clear()


def _create_test_action():
    return pa.create(
        agent_id="test-agent",
        session_id="sess-001",
        sql="DELETE FROM users WHERE id = 1",
        action_type="DELETE",
        risk_level="high",
        summary="Deletar usuário com id=1",
        database="testdb",
        ttl_seconds=300,
    )


def test_create_pending_action():
    action = _create_test_action()
    assert action.id.startswith("pa_")
    assert action.status == "pending"
    assert action.agent_id == "test-agent"
    assert action.sql == "DELETE FROM users WHERE id = 1"


def test_get_pending_action():
    action = _create_test_action()
    found = pa.get(action.id)
    assert found is not None
    assert found.id == action.id


def test_confirm_pending_action():
    action = _create_test_action()
    success, reason, confirmed = pa.confirm(action.id, "test-agent", "sess-001")
    assert success is True
    assert confirmed is not None
    assert confirmed.status == "confirmed"


def test_confirm_wrong_agent_fails():
    action = _create_test_action()
    success, reason, _ = pa.confirm(action.id, "other-agent", "sess-001")
    assert success is False
    assert "não pertence" in reason


def test_confirm_wrong_session_fails():
    action = _create_test_action()
    success, reason, _ = pa.confirm(action.id, "test-agent", "sess-wrong")
    assert success is False


def test_cancel_pending_action():
    action = _create_test_action()
    success, reason = pa.cancel(action.id, "test-agent", "sess-001")
    assert success is True
    assert pa.get(action.id).status == "cancelled"


def test_cancel_then_confirm_fails():
    action = _create_test_action()
    pa.cancel(action.id, "test-agent", "sess-001")
    success, reason, _ = pa.confirm(action.id, "test-agent", "sess-001")
    assert success is False


def test_list_by_agent():
    _create_test_action()
    _create_test_action()
    actions = pa.list_by_agent("test-agent")
    assert len(actions) == 2


def test_mark_executed():
    action = _create_test_action()
    pa.confirm(action.id, "test-agent", "sess-001")
    result = pa.mark_executed(action.id, {"success": True})
    assert result is True
    assert pa.get(action.id).status == "executed"


def test_nonexistent_action():
    assert pa.get("nonexistent") is None
    success, _, _ = pa.confirm("nonexistent", "a", "b")
    assert success is False
