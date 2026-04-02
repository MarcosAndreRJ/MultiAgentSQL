"""
Testes para o AliasService.
Cobre: geração de aliases automáticos, aliases manuais, prioridade, persistência.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.schemas.digest import AliasData, DBDigest, DigestSummary, TableDigest


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_digest(agent_id: str, table_names: list[str]) -> DBDigest:
    return DBDigest(
        agent_id=agent_id,
        database="testdb",
        summary=DigestSummary(tables=len(table_names)),
        tables=[TableDigest(name=n) for n in table_names],
    )


# ─── Testes de geração automática ─────────────────────────────────────────────

def test_generate_tokens_single():
    from app.services.alias_service import _generate_tokens

    tokens = _generate_tokens("Dica")
    assert "@Dica" in tokens
    assert "@Dicas" in tokens


def test_generate_tokens_plural_vowel():
    from app.services.alias_service import _generate_tokens

    tokens = _generate_tokens("Proposta")
    assert "@Proposta" in tokens
    assert "@Propostas" in tokens


def test_generate_tokens_plural_z():
    from app.services.alias_service import _generate_tokens

    tokens = _generate_tokens("Vez")
    assert "@Vez" in tokens
    assert "@Vezes" in tokens


def test_generate_tokens_already_s():
    """Tabelas que já terminam em 's' não devem gerar plural extra."""
    from app.services.alias_service import _generate_tokens

    tokens = _generate_tokens("Users")
    assert "@Users" in tokens
    # não deve ter @Userss
    assert "@Userss" not in tokens


def test_generate_tokens_consonant():
    from app.services.alias_service import _generate_tokens

    tokens = _generate_tokens("Projeto")
    # termina em 'o' (vogal) → plural com 's'
    assert "@Projetos" in tokens


def test_generate_aliases_from_digest(tmp_path):
    """Deve gerar aliases corretos para todas as tabelas."""
    from app.services.alias_service import generate_aliases_from_digest

    digest = _make_digest("ag1", ["Dica", "Projeto", "Users"])

    with patch("app.services.alias_service.settings") as mock_settings:
        mock_settings.aliases_path = tmp_path

        data = generate_aliases_from_digest(digest)

        assert data.agent_id == "ag1"
        assert data.aliases["@Dica"] == "Dica"
        assert data.aliases["@Dicas"] == "Dica"
        assert data.aliases["@Projeto"] == "Projeto"
        assert data.aliases["@Projetos"] == "Projeto"
        assert data.aliases["@Users"] == "Users"

        # Arquivo deve ter sido criado
        assert (tmp_path / "ag1.aliases.json").exists()


def test_generate_aliases_preserves_manual(tmp_path):
    """Deve preservar manual_aliases ao regenerar."""
    from app.services.alias_service import generate_aliases_from_digest

    # Pré-popular arquivo com alias manual
    aliases_file = tmp_path / "prsv.aliases.json"
    aliases_file.write_text(
        json.dumps({
            "agent_id": "prsv",
            "database": "testdb",
            "generated_at": "2026-01-01T00:00:00",
            "aliases": {},
            "manual_aliases": {"@Hints": "Dica"},
        }),
        encoding="utf-8",
    )

    digest = _make_digest("prsv", ["Dica"])

    with patch("app.services.alias_service.settings") as mock_settings:
        mock_settings.aliases_path = tmp_path

        data = generate_aliases_from_digest(digest)
        assert data.manual_aliases.get("@Hints") == "Dica"


# ─── Testes de CRUD manual ────────────────────────────────────────────────────

def test_add_manual_alias(tmp_path):
    from app.services.alias_service import add_manual_alias, load_aliases

    with patch("app.services.alias_service.settings") as mock_settings:
        mock_settings.aliases_path = tmp_path

        result = add_manual_alias("ag2", "@Hints", "Dica")
        assert result.manual_aliases["@Hints"] == "Dica"

        loaded = load_aliases("ag2")
        assert loaded is not None
        assert loaded.manual_aliases["@Hints"] == "Dica"


def test_add_manual_alias_normalizes_at(tmp_path):
    """Deve adicionar '@' se não estiver presente."""
    from app.services.alias_service import add_manual_alias

    with patch("app.services.alias_service.settings") as mock_settings:
        mock_settings.aliases_path = tmp_path

        result = add_manual_alias("ag3", "SemArroba", "TabelaX")
        # _normalize_token adiciona @
        assert result.manual_aliases.get("@SemArroba") == "TabelaX"


def test_remove_manual_alias(tmp_path):
    from app.services.alias_service import add_manual_alias, remove_manual_alias, load_aliases

    with patch("app.services.alias_service.settings") as mock_settings:
        mock_settings.aliases_path = tmp_path

        add_manual_alias("ag4", "@Temp", "TabelaA")
        remove_manual_alias("ag4", "@Temp")

        loaded = load_aliases("ag4")
        assert "@Temp" not in (loaded.manual_aliases or {})


def test_load_aliases_returns_none_missing(tmp_path):
    from app.services.alias_service import load_aliases

    with patch("app.services.alias_service.settings") as mock_settings:
        mock_settings.aliases_path = tmp_path
        assert load_aliases("ghost-agent") is None


# ─── Testes de prioridade ──────────────────────────────────────────────────────

def test_manual_overrides_auto(tmp_path):
    """manual_aliases deve ter prioridade sobre aliases automáticos."""
    from app.services.alias_service import generate_aliases_from_digest, add_manual_alias

    digest = _make_digest("ag5", ["Dica"])

    with patch("app.services.alias_service.settings") as mock_settings:
        mock_settings.aliases_path = tmp_path

        # Gera automáticos: @Dicas → Dica
        generate_aliases_from_digest(digest)

        # Adiciona manual que sobrescreve @Dicas para outra tabela
        add_manual_alias("ag5", "@Dicas", "OutraTabela")

        from app.services.alias_service import load_aliases
        loaded = load_aliases("ag5")
        # manual_aliases tem @Dicas → OutraTabela
        assert loaded.manual_aliases["@Dicas"] == "OutraTabela"
        # aliases automáticos mantêm o valor original
        assert loaded.aliases["@Dicas"] == "Dica"
