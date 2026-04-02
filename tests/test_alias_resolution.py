"""
Testes de resolução de aliases em mensagens e integração com prompt builder.
Cobre: resolve_message_aliases, prioridade manual > auto, integração prompt.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.digest import AliasData, DBDigest, DigestSummary, TableDigest


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _write_aliases(tmp_path: Path, agent_id: str, aliases: dict, manual: dict = None):
    data = {
        "agent_id": agent_id,
        "database": "testdb",
        "generated_at": "2026-03-23T00:00:00",
        "aliases": aliases,
        "manual_aliases": manual or {},
    }
    (tmp_path / f"{agent_id}.aliases.json").write_text(
        json.dumps(data), encoding="utf-8"
    )


# ─── Testes de resolve_message_aliases ────────────────────────────────────────

def test_resolve_single_alias(tmp_path):
    from app.services.alias_service import resolve_message_aliases

    _write_aliases(tmp_path, "ag1", {"@dica": "Dica", "@dicas": "Dica"})

    with patch("app.services.alias_service.settings") as mock_settings:
        mock_settings.aliases_path = tmp_path

        resolved, hits = resolve_message_aliases("ag1", "quantos registros tem @Dicas")
        assert "@Dicas" not in resolved
        assert "Dica" in resolved
        assert hits.get("@Dicas") == "Dica"


def test_resolve_multiple_aliases(tmp_path):
    from app.services.alias_service import resolve_message_aliases

    _write_aliases(tmp_path, "ag2", {
        "@dica": "Dica",
        "@projeto": "Projeto",
    })

    with patch("app.services.alias_service.settings") as mock_settings:
        mock_settings.aliases_path = tmp_path

        resolved, hits = resolve_message_aliases(
            "ag2", "join @Dica com @Projeto onde @Dica.id = @Projeto.dica_id"
        )
        assert "Dica" in resolved
        assert "Projeto" in resolved
        assert len(hits) == 2


def test_resolve_case_insensitive(tmp_path):
    """A resolução deve ser case-insensitive no lookup."""
    from app.services.alias_service import resolve_message_aliases

    _write_aliases(tmp_path, "ag3", {"@dica": "Dica"})

    with patch("app.services.alias_service.settings") as mock_settings:
        mock_settings.aliases_path = tmp_path

        resolved, hits = resolve_message_aliases("ag3", "mostre @DICA")
        assert "Dica" in resolved
        assert hits.get("@DICA") == "Dica"


def test_resolve_unknown_alias_unchanged(tmp_path):
    """Tokens não mapeados devem permanecer exatamente como estão."""
    from app.services.alias_service import resolve_message_aliases

    _write_aliases(tmp_path, "ag4", {"@dica": "Dica"})

    with patch("app.services.alias_service.settings") as mock_settings:
        mock_settings.aliases_path = tmp_path

        resolved, hits = resolve_message_aliases("ag4", "mostre @Desconhecido")
        assert "@Desconhecido" in resolved
        assert "Desconhecido" not in hits or hits.get("@Desconhecido") is None


def test_resolve_no_aliases_file_returns_original(tmp_path):
    """Sem arquivo de aliases, deve retornar a mensagem original sem erro."""
    from app.services.alias_service import resolve_message_aliases

    with patch("app.services.alias_service.settings") as mock_settings:
        mock_settings.aliases_path = tmp_path

        resolved, hits = resolve_message_aliases("ghost", "mensagem com @Algo")
        assert resolved == "mensagem com @Algo"
        assert hits == {}


def test_manual_alias_priority(tmp_path):
    """manual_aliases devem ter prioridade sobre aliases automáticos."""
    from app.services.alias_service import resolve_message_aliases

    _write_aliases(
        tmp_path,
        "ag5",
        aliases={"@dica": "Dica"},
        manual={"@dica": "OutraTabela"},
    )

    with patch("app.services.alias_service.settings") as mock_settings:
        mock_settings.aliases_path = tmp_path

        resolved, hits = resolve_message_aliases("ag5", "veja @Dica")
        assert "OutraTabela" in resolved
        assert hits.get("@Dica") == "OutraTabela"


def test_resolve_empty_message(tmp_path):
    from app.services.alias_service import resolve_message_aliases

    _write_aliases(tmp_path, "ag6", {"@dica": "Dica"})

    with patch("app.services.alias_service.settings") as mock_settings:
        mock_settings.aliases_path = tmp_path

        resolved, hits = resolve_message_aliases("ag6", "")
        assert resolved == ""
        assert hits == {}


def test_resolve_message_no_at_tokens(tmp_path):
    from app.services.alias_service import resolve_message_aliases

    _write_aliases(tmp_path, "ag7", {"@dica": "Dica"})

    with patch("app.services.alias_service.settings") as mock_settings:
        mock_settings.aliases_path = tmp_path

        resolved, hits = resolve_message_aliases("ag7", "listar tabelas do banco")
        assert resolved == "listar tabelas do banco"
        assert hits == {}


# ─── Integração com prompt builder ────────────────────────────────────────────

def test_build_digest_context_no_digest(tmp_path):
    """Sem digest, build_digest_context deve retornar string vazia."""
    from app.agents.prompt_builder import build_digest_context

    with patch("app.agents.prompt_builder.settings") as ms, \
         patch("app.services.digest_service.settings") as ds:
        ms.digests_path = tmp_path
        ds.digests_path = tmp_path

        result = build_digest_context("no-agent", "qualquer mensagem")
        assert result == ""


def test_build_digest_context_summary_always_included(tmp_path):
    """Com digest presente, o resumo sempre aparece no contexto."""
    from app.agents.prompt_builder import build_digest_context

    digest = DBDigest(
        agent_id="ctx-agent",
        database="ctx_db",
        summary=DigestSummary(tables=5, views=1, triggers=2),
        tables=[TableDigest(name="Orders")],
    )

    import json
    digest_file = tmp_path / "ctx-agent.digest.json"
    digest_file.write_text(digest.model_dump_json(), encoding="utf-8")

    with patch("app.services.digest_service.settings") as ds:
        ds.digests_path = tmp_path

        result = build_digest_context("ctx-agent", "mensagem genérica")
        assert "5" in result  # tabelas
        assert "ctx_db" in result


def test_build_digest_context_injects_relevant_table(tmp_path):
    """Mensagem que menciona tabela específica injeta detalhe."""
    from app.agents.prompt_builder import build_digest_context

    digest = DBDigest(
        agent_id="ctx-agent2",
        database="db",
        summary=DigestSummary(tables=2),
        tables=[
            TableDigest(name="Dica", description="Tabela de dicas"),
            TableDigest(name="Projeto", description="Tabela de projetos"),
        ],
    )

    digest_file = tmp_path / "ctx-agent2.digest.json"
    digest_file.write_text(digest.model_dump_json(), encoding="utf-8")

    with patch("app.services.digest_service.settings") as ds:
        ds.digests_path = tmp_path

        result = build_digest_context("ctx-agent2", "quantos registros na tabela Dica?")
        assert "Dica" in result
        assert "Tabela de dicas" in result


def test_build_digest_context_no_irrelevant_detail(tmp_path):
    """Mensagem genérica não injeta detalhes de tabelas específicas."""
    from app.agents.prompt_builder import build_digest_context

    digest = DBDigest(
        agent_id="ctx-agent3",
        database="db",
        summary=DigestSummary(tables=2),
        tables=[
            TableDigest(name="Dica"),
            TableDigest(name="Projeto"),
        ],
    )

    digest_file = tmp_path / "ctx-agent3.digest.json"
    digest_file.write_text(digest.model_dump_json(), encoding="utf-8")

    with patch("app.services.digest_service.settings") as ds:
        ds.digests_path = tmp_path

        result = build_digest_context("ctx-agent3", "listar tabelas")
        # Deve conter resumo mas não seção detalhada de tabela específica
        assert "## Detalhes" not in result


# ─── Integração com chat_service ──────────────────────────────────────────────

def test_chat_service_resolve_aliases_helper(tmp_path):
    """_resolve_aliases deve retornar mensagem sem aliases e mapeamento."""
    from app.services.chat_service import _resolve_aliases

    _write_aliases(tmp_path, "chat-ag", {"@dica": "Dica", "@dicas": "Dica"})

    with patch("app.services.alias_service.settings") as mock_settings:
        mock_settings.aliases_path = tmp_path

        resolved, hits = _resolve_aliases("chat-ag", "contar @Dicas")
        assert "Dica" in resolved
        assert "@Dicas" not in resolved
        assert hits


def test_chat_service_resolve_aliases_no_file(tmp_path):
    """Sem arquivo de aliases, deve devolver mensagem original sem erro."""
    from app.services.chat_service import _resolve_aliases

    with patch("app.services.alias_service.settings") as mock_settings:
        mock_settings.aliases_path = tmp_path

        resolved, hits = _resolve_aliases("ghost-ag", "mensagem @Tabela")
        assert resolved == "mensagem @Tabela"
        assert hits == {}
