"""
Testes para o DigestService.
Cobre: geração de digest, persistência em JSON e MD, heurísticas.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.digest import (
    ColumnInfo,
    DBDigest,
    DigestSummary,
    ForeignKeyInfo,
    TableDigest,
    TriggerDigest,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def _make_db_result(rows: list[dict], success: bool = True) -> MagicMock:
    r = MagicMock()
    r.success = success
    r.rows = rows
    r.error = "" if success else "Erro simulado"
    r.columns = list(rows[0].keys()) if rows else []
    return r


def _make_agent(agent_id: str = "test-agent", db_name: str = "test_db") -> MagicMock:
    agent = MagicMock()
    agent.id = agent_id
    agent.database = MagicMock()
    agent.database.name = db_name
    return agent


# ─── Testes de persistência ────────────────────────────────────────────────────

def test_persist_json_creates_file(tmp_path):
    """Deve criar o arquivo JSON do digest no caminho correto."""
    from app.services.digest_service import _persist_json, _json_path

    with patch("app.services.digest_service.settings") as mock_settings:
        mock_settings.digests_path = tmp_path

        digest = DBDigest(
            agent_id="myagent",
            database="mydb",
            generated_at=datetime(2026, 3, 23, 12, 0, 0),
            summary=DigestSummary(tables=2, views=1, triggers=0, procedures=0, functions=0),
            tables=[TableDigest(name="Users", type="BASE TABLE", primary_key="id")],
        )
        _persist_json(digest)

        out = tmp_path / "myagent.digest.json"
        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["agent_id"] == "myagent"
        assert data["summary"]["tables"] == 2
        assert data["tables"][0]["name"] == "Users"


def test_persist_md_creates_file(tmp_path):
    """Deve criar o arquivo Markdown do digest."""
    from app.services.digest_service import _persist_md

    with patch("app.services.digest_service.settings") as mock_settings:
        mock_settings.digests_path = tmp_path

        digest = DBDigest(
            agent_id="myagent",
            database="mydb",
            summary=DigestSummary(tables=1, views=0, triggers=0, procedures=0, functions=0),
            tables=[TableDigest(name="Products", description="Catálogo", primary_key="id")],
        )
        _persist_md(digest)

        out = tmp_path / "myagent.digest.md"
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "# DB Digest" in content
        assert "Products" in content
        assert "Catálogo" in content


def test_load_digest_returns_none_when_missing(tmp_path):
    """Deve retornar None quando o arquivo não existe."""
    from app.services.digest_service import load_digest

    with patch("app.services.digest_service.settings") as mock_settings:
        mock_settings.digests_path = tmp_path
        assert load_digest("nonexistent-agent") is None


def test_load_digest_roundtrip(tmp_path):
    """Deve carregar de volta o mesmo digest que foi salvo."""
    from app.services.digest_service import _persist_json, load_digest

    with patch("app.services.digest_service.settings") as mock_settings:
        mock_settings.digests_path = tmp_path

        digest = DBDigest(
            agent_id="roundtrip",
            database="testdb",
            summary=DigestSummary(tables=3, views=0, triggers=1, procedures=0, functions=0),
            tables=[
                TableDigest(
                    name="Orders",
                    type="BASE TABLE",
                    primary_key="id",
                    columns=[ColumnInfo(name="id", type="int", nullable=False)],
                )
            ],
        )
        _persist_json(digest)
        loaded = load_digest("roundtrip")
        assert loaded is not None
        assert loaded.database == "testdb"
        assert loaded.summary.tables == 3
        assert loaded.tables[0].name == "Orders"
        assert loaded.tables[0].primary_key == "id"


# ─── Testes de heurística ──────────────────────────────────────────────────────

def test_heuristic_description_log_table():
    from app.services.digest_service import _heuristic_description

    desc = _heuristic_description("audit_log", [], [])
    assert "log" in desc.lower() or "auditoria" in desc.lower()


def test_heuristic_description_user_table():
    from app.services.digest_service import _heuristic_description

    desc = _heuristic_description("users", [ColumnInfo(name="id", type="int")], [])
    assert "usuário" in desc.lower() or "user" in desc.lower() or "pessoa" in desc.lower()


def test_heuristic_description_with_fk():
    from app.services.digest_service import _heuristic_description

    cols = [ColumnInfo(name="id", type="int"), ColumnInfo(name="category_id", type="int")]
    fks = [ForeignKeyInfo(constraint_name="fk1", column="category_id", ref_table="Category", ref_column="id")]
    desc = _heuristic_description("Product", cols, fks)
    assert "Category" in desc


def test_heuristic_description_fallback():
    from app.services.digest_service import _heuristic_description

    desc = _heuristic_description("ZZZUnknown", [], [])
    assert "ZZZUnknown" in desc or len(desc) > 0


# ─── Testes de coleta ──────────────────────────────────────────────────────────

def test_collect_tables_returns_empty_on_failure():
    from app.services.digest_service import _collect_tables

    agent = _make_agent()
    with patch("app.services.digest_service.db_introspection.list_tables") as mock_list:
        mock_list.return_value = _make_db_result([], success=False)
        result = _collect_tables(agent)
        assert result == []


def test_collect_tables_builds_digest():
    from app.services.digest_service import _collect_tables

    agent = _make_agent()
    table_rows = [{"Tables_in_test_db (BASE TABLE)": "Dica"}]
    col_rows = [
        {"COLUMN_NAME": "id", "COLUMN_TYPE": "int", "IS_NULLABLE": "NO", "EXTRA": "auto_increment"},
        {"COLUMN_NAME": "titulo", "COLUMN_TYPE": "varchar(255)", "IS_NULLABLE": "YES", "EXTRA": ""},
    ]

    with patch("app.services.digest_service.db_introspection.list_tables") as mock_list, \
         patch("app.services.digest_service.db_introspection.get_columns") as mock_cols, \
         patch("app.services.digest_service.db_introspection.get_foreign_keys") as mock_fks:

        mock_list.return_value = _make_db_result(table_rows)
        mock_cols.return_value = _make_db_result(col_rows)
        mock_fks.return_value = _make_db_result([])

        result = _collect_tables(agent)
        assert len(result) == 1
        assert result[0].name == "Dica"
        assert result[0].primary_key == "id"
        assert len(result[0].columns) == 2


def test_get_digest_status_not_exists(tmp_path):
    from app.services.digest_service import get_digest_status

    with patch("app.services.digest_service.settings") as mock_settings:
        mock_settings.digests_path = tmp_path
        status = get_digest_status("no-agent")
        assert not status.exists
        assert status.tables == 0


def test_get_digest_status_exists(tmp_path):
    from app.services.digest_service import _persist_json, get_digest_status

    with patch("app.services.digest_service.settings") as mock_settings:
        mock_settings.digests_path = tmp_path

        digest = DBDigest(
            agent_id="check-agent",
            database="db",
            summary=DigestSummary(tables=5, views=2, triggers=1),
        )
        _persist_json(digest)

        status = get_digest_status("check-agent")
        assert status.exists
        assert status.tables == 5
        assert status.views == 2
        assert status.triggers == 1
