"""
Tests: Guard Engine
"""
import pytest
from app.core.guard_engine import evaluate
from app.schemas.agent import AgentConfig, AgentPermissions, AgentGuards, AgentBehavior


def _make_agent(perm_overrides=None, guard_overrides=None) -> AgentConfig:
    perm_data = {
        "can_read_db": True,
        "can_write_db": True,
        "can_ddl": True,
        "can_execute": True,
    }
    perm_data.update(perm_overrides or {})
    perms = AgentPermissions(**perm_data)

    guard_data = {
        "require_confirmation_for": ["DELETE", "DROP", "TRUNCATE", "UPDATE_WITHOUT_WHERE", "ALTER_DESTRUCTIVE"],
        "auto_approve": ["SELECT", "SHOW", "DESCRIBE", "EXPLAIN"],
    }
    guard_data.update(guard_overrides or {})
    guards = AgentGuards(**guard_data)
    return AgentConfig(
        id="test-agent",
        name="Test Agent",
        description="Test",
        type="mysql-specialist",
        model="llama3.1:8b",
        prompt_file="",
        skills=[],
        database=None,
        permissions=perms,
        guards=guards,
        behavior=AgentBehavior(),
    )


def test_select_is_allowed_without_confirmation():
    agent = _make_agent()
    decision = evaluate("SELECT * FROM users", agent)
    assert decision.allowed is True
    assert decision.requires_confirmation is False


def test_delete_requires_confirmation():
    agent = _make_agent()
    decision = evaluate("DELETE FROM users WHERE id = 1", agent)
    assert decision.allowed is True
    assert decision.requires_confirmation is True
    assert decision.risk_level == "high"


def test_drop_requires_confirmation():
    agent = _make_agent()
    decision = evaluate("DROP TABLE users", agent)
    assert decision.allowed is True
    assert decision.requires_confirmation is True


def test_update_without_where_requires_confirmation():
    agent = _make_agent()
    decision = evaluate("UPDATE users SET active = 0", agent)
    assert decision.allowed is True
    assert decision.requires_confirmation is True


def test_agent_without_execute_blocked():
    agent = _make_agent(perm_overrides={"can_execute": False})
    decision = evaluate("SELECT 1", agent)
    assert decision.allowed is False


def test_agent_without_ddl_blocked():
    agent = _make_agent(perm_overrides={"can_ddl": False})
    decision = evaluate("DROP TABLE users", agent)
    assert decision.allowed is False


def test_protected_table_blocked():
    agent = _make_agent(perm_overrides={"protected_tables": ["audit_log"]})
    decision = evaluate("DELETE FROM audit_log WHERE id = 1", agent)
    assert decision.allowed is False


def test_show_auto_approved():
    agent = _make_agent()
    decision = evaluate("SHOW TABLES", agent)
    assert decision.allowed is True
    assert decision.requires_confirmation is False


def test_truncate_requires_confirmation():
    agent = _make_agent()
    decision = evaluate("TRUNCATE TABLE orders", agent)
    assert decision.allowed is True
    assert decision.requires_confirmation is True
