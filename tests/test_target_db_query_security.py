from __future__ import annotations

import pytest

from app.services.target_db.query_service import validate_and_format_query, _enforce_access_mode


def test_validate_query_injects_limit():
    out = validate_and_format_query("SELECT * FROM clientes")
    assert "LIMIT 100" in out.upper()


def test_validate_query_blocks_multi_statement():
    with pytest.raises(ValueError):
        validate_and_format_query("SELECT 1; SELECT 2")


def test_validate_query_blocks_write_command():
    with pytest.raises(ValueError):
        validate_and_format_query("DELETE FROM clientes")


def test_enforce_access_mode_rejects_invalid_mode():
    with pytest.raises(ValueError):
        _enforce_access_mode("invalid", "SELECT 1")
