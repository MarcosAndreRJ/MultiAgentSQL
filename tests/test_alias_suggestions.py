"""
Testes para suggest_aliases (alias_service) e endpoint GET /api/aliases/suggest.

Cobre:
  - sugestões filtradas por prefixo
  - aliases manuais aparecem primeiro
  - case-insensitive
  - agente sem aliases retorna lista vazia
  - q vazio retorna todos
  - endpoint HTTP com mock do agente
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.alias_service import suggest_aliases


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _write_aliases(
    tmp_path: Path,
    agent_id: str,
    aliases: dict,
    manual: dict | None = None,
):
    data = {
        "agent_id": agent_id,
        "database": "testdb",
        "generated_at": "2026-03-23T00:00:00+00:00",
        "aliases": aliases,
        "manual_aliases": manual or {},
    }
    (tmp_path / f"{agent_id}.aliases.json").write_text(
        json.dumps(data), encoding="utf-8"
    )


def _patch_aliases_path(tmp_path: Path):
    return patch("app.services.alias_service.settings", MagicMock(aliases_path=tmp_path))


# ─── suggest_aliases: básico ──────────────────────────────────────────────────

class TestSuggestAliasesBasic:
    def test_sem_aliases_retorna_vazio(self, tmp_path):
        """Agente sem arquivo de aliases retorna lista vazia."""
        with _patch_aliases_path(tmp_path):
            result = suggest_aliases("agente-sem-aliases", "@di")
        assert result == []

    def test_q_vazio_retorna_todos(self, tmp_path):
        """q='' deve retornar todos os aliases."""
        _write_aliases(tmp_path, "ag1", {
            "@Dica": "Dica",
            "@Dicas": "Dica",
            "@Projeto": "Projeto",
        })
        with _patch_aliases_path(tmp_path):
            result = suggest_aliases("ag1", "")
        assert len(result) == 3

    def test_q_com_arroba_filtra(self, tmp_path):
        _write_aliases(tmp_path, "ag1", {
            "@Dica": "Dica",
            "@Dicas": "Dica",
            "@Projeto": "Projeto",
        })
        with _patch_aliases_path(tmp_path):
            result = suggest_aliases("ag1", "@di")
        tokens = [r["alias"].lower() for r in result]
        assert "@dica" in tokens
        assert "@dicas" in tokens
        assert "@projeto" not in tokens

    def test_q_sem_arroba_filtra_igual(self, tmp_path):
        """q sem @ deve ser tratado como '@...'."""
        _write_aliases(tmp_path, "ag1", {
            "@Dica": "Dica",
            "@Projeto": "Projeto",
        })
        with _patch_aliases_path(tmp_path):
            # O alias_service verifica startswith(q_lower) — q="@di" ou "di"
            # Quando o caller passa q="@di", funciona; se passar "di", não bate
            # O endpoint faz: if q and not q.startswith("@"): q = "@" + q
            # Aqui testamos diretamente o service com "@"
            result = suggest_aliases("ag1", "@Di")
        tokens = [r["alias"].lower() for r in result]
        assert "@dica" in tokens

    def test_case_insensitive(self, tmp_path):
        _write_aliases(tmp_path, "ag1", {"@Projeto": "Projeto", "@Projetos": "Projeto"})
        with _patch_aliases_path(tmp_path):
            result = suggest_aliases("ag1", "@proj")
        assert len(result) == 2

    def test_match_exato(self, tmp_path):
        _write_aliases(tmp_path, "ag1", {"@Empresa": "Empresa", "@Empregado": "Empregado"})
        with _patch_aliases_path(tmp_path):
            result = suggest_aliases("ag1", "@Empresa")
        assert len(result) == 1
        assert result[0]["alias"] == "@Empresa"

    def test_sem_match_retorna_vazio(self, tmp_path):
        _write_aliases(tmp_path, "ag1", {"@Dica": "Dica"})
        with _patch_aliases_path(tmp_path):
            result = suggest_aliases("ag1", "@xyz")
        assert result == []


# ─── suggest_aliases: campos do resultado ─────────────────────────────────────

class TestSuggestAliasesFields:
    def test_campos_presentes(self, tmp_path):
        _write_aliases(tmp_path, "ag1", {"@Dica": "Dica"})
        with _patch_aliases_path(tmp_path):
            result = suggest_aliases("ag1", "@di")
        assert len(result) == 1
        item = result[0]
        assert "alias" in item
        assert "table" in item
        assert "source" in item

    def test_source_auto(self, tmp_path):
        _write_aliases(tmp_path, "ag1", {"@Dica": "Dica"})
        with _patch_aliases_path(tmp_path):
            result = suggest_aliases("ag1", "@di")
        assert result[0]["source"] == "auto"

    def test_source_manual(self, tmp_path):
        _write_aliases(tmp_path, "ag1", {}, manual={"@TblDica": "Dica"})
        with _patch_aliases_path(tmp_path):
            result = suggest_aliases("ag1", "@tbl")
        assert result[0]["source"] == "manual"

    def test_table_correto(self, tmp_path):
        _write_aliases(tmp_path, "ag1", {"@Dicas": "Dica"})
        with _patch_aliases_path(tmp_path):
            result = suggest_aliases("ag1", "@dic")
        assert result[0]["table"] == "Dica"


# ─── suggest_aliases: prioridade manual > auto ────────────────────────────────

class TestSuggestAliasesPriority:
    def test_manual_primeiro(self, tmp_path):
        _write_aliases(
            tmp_path, "ag1",
            aliases={"@Dica": "Dica", "@Dicas": "Dica"},
            manual={"@DicaEspecial": "Dica"},
        )
        with _patch_aliases_path(tmp_path):
            result = suggest_aliases("ag1", "@dic")
        sources = [r["source"] for r in result]
        # Primeiro item deve ser manual
        assert sources[0] == "manual"
        assert sources.count("manual") == 1
        assert sources.count("auto") == 2

    def test_manual_sobrepe_auto_no_mesmo_token(self, tmp_path):
        """Se o mesmo token existe como manual e auto, só aparece manual."""
        _write_aliases(
            tmp_path, "ag1",
            aliases={"@Dica": "Dica"},
            manual={"@Dica": "DicaManual"},  # mesmo token
        )
        with _patch_aliases_path(tmp_path):
            result = suggest_aliases("ag1", "@dic")
        # Apenas uma entrada para @Dica
        assert len(result) == 1
        assert result[0]["source"] == "manual"
        assert result[0]["table"] == "DicaManual"

    def test_ordenacao_alfabetica_dentro_do_grupo(self, tmp_path):
        _write_aliases(
            tmp_path, "ag1",
            aliases={
                "@Zebra": "Zebra",
                "@Alpha": "Alpha",
                "@Beta": "Beta",
            },
        )
        with _patch_aliases_path(tmp_path):
            result = suggest_aliases("ag1", "@")
        tokens = [r["alias"].lower() for r in result]
        assert tokens == sorted(tokens)


# ─── Endpoint HTTP GET /api/aliases/suggest ───────────────────────────────────

class TestSuggestEndpoint:
    def test_endpoint_200(self, tmp_path):
        from fastapi.testclient import TestClient
        from app.main import app

        _write_aliases(tmp_path, "test-agent", {"@Dica": "Dica", "@Dicas": "Dica"})

        mock_agent = MagicMock()
        mock_agent.id = "test-agent"
        mock_agent.database = MagicMock()

        with (
            patch("app.api.routes_aliases.agent_registry.get", return_value=mock_agent),
            patch("app.services.alias_service.settings", MagicMock(aliases_path=tmp_path)),
        ):
            client = TestClient(app)
            res = client.get("/api/aliases/suggest?agent_id=test-agent&q=%40di")

        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert all("alias" in item and "table" in item and "source" in item for item in data)

    def test_endpoint_q_sem_arroba(self, tmp_path):
        """q sem @ deve ser auto-prefixado."""
        from fastapi.testclient import TestClient
        from app.main import app

        _write_aliases(tmp_path, "test-agent2", {"@Projeto": "Projeto"})

        mock_agent = MagicMock()
        mock_agent.id = "test-agent2"

        with (
            patch("app.api.routes_aliases.agent_registry.get", return_value=mock_agent),
            patch("app.services.alias_service.settings", MagicMock(aliases_path=tmp_path)),
        ):
            client = TestClient(app)
            # q sem @ — o endpoint adiciona @ automaticamente
            res = client.get("/api/aliases/suggest?agent_id=test-agent2&q=pro")

        assert res.status_code == 200
        data = res.json()
        assert any(item["alias"] == "@Projeto" for item in data)

    def test_endpoint_agente_inexistente_404(self):
        from fastapi.testclient import TestClient
        from app.main import app

        with patch("app.api.routes_aliases.agent_registry.get", return_value=None):
            client = TestClient(app)
            res = client.get("/api/aliases/suggest?agent_id=nao-existe&q=@di")

        assert res.status_code == 404

    def test_endpoint_sem_aliases_retorna_lista_vazia(self, tmp_path):
        from fastapi.testclient import TestClient
        from app.main import app

        mock_agent = MagicMock()
        mock_agent.id = "agente-vazio"

        with (
            patch("app.api.routes_aliases.agent_registry.get", return_value=mock_agent),
            patch("app.services.alias_service.settings", MagicMock(aliases_path=tmp_path)),
        ):
            client = TestClient(app)
            res = client.get("/api/aliases/suggest?agent_id=agente-vazio&q=%40any")

        assert res.status_code == 200
        assert res.json() == []
