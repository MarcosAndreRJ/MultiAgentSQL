"""
Tests: LLM Plan validation (parser in ollama_client)
"""
import pytest
from app.services.ollama_client import _parse_llm_plan


def test_valid_json_plan():
    raw = '{"intent": "query", "needs_tools": true, "tools": [], "sql": "SELECT * FROM users", "explanation": "Consultar users", "risk_hint": "low"}'
    plan = _parse_llm_plan(raw)
    assert plan.intent == "query"
    assert plan.needs_tools is True
    assert plan.sql == "SELECT * FROM users"
    assert plan.risk_hint == "low"


def test_json_in_markdown_block():
    raw = '''```json
{"intent": "ddl", "needs_tools": false, "tools": [], "sql": null, "explanation": "Explicação", "risk_hint": "low"}
```'''
    plan = _parse_llm_plan(raw)
    assert plan.intent == "ddl"
    assert plan.sql is None


def test_invalid_intent_fallsback_to_unknown():
    raw = '{"intent": "invalid_type", "needs_tools": false, "tools": [], "explanation": "test", "risk_hint": "low"}'
    plan = _parse_llm_plan(raw)
    assert plan.intent == "unknown"


def test_invalid_json_fallsback_gracefully():
    raw = "Este é um texto livre, não JSON."
    plan = _parse_llm_plan(raw)
    # Deve retornar um plano de fallback sem lançar exceção
    assert plan.intent == "explain"
    assert plan.needs_tools is False
    assert "Este é um texto livre" in plan.explanation


def test_empty_response_fallsback():
    plan = _parse_llm_plan("")
    assert plan.intent == "explain"
    assert plan.needs_tools is False


def test_risk_hint_invalid_defaults_to_low():
    raw = '{"intent": "query", "needs_tools": false, "tools": [], "explanation": "test", "risk_hint": "extreme"}'
    plan = _parse_llm_plan(raw)
    assert plan.risk_hint == "low"


def test_sql_stripped_of_whitespace():
    raw = '{"intent": "write", "needs_tools": true, "tools": [], "sql": "  INSERT INTO t VALUES (1)  ", "explanation": "x", "risk_hint": "medium"}'
    plan = _parse_llm_plan(raw)
    assert plan.sql == "INSERT INTO t VALUES (1)"


def test_tools_validated_as_list():
    raw = '{"intent": "query", "needs_tools": true, "tools": "not-a-list", "explanation": "x", "risk_hint": "low"}'
    plan = _parse_llm_plan(raw)
    assert isinstance(plan.tools, list)
    assert plan.tools == []
