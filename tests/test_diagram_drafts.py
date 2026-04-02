"""
Tests: diagram_draft_service

Verifica:
- get_draft retorna draft vazio quando arquivo não existe
- add_table persiste DraftTable
- add_table substitui tabela com mesmo nome
- remove_table remove pelo nome e retorna True
- remove_table retorna False quando tabela não existe
- promote_table equivale a remove
- clear_all remove o arquivo
"""
import pytest
from pathlib import Path
from unittest.mock import patch

from app.schemas.draft import AddDraftTableRequest, DiagramDraft, DraftColumn, DraftTable
from app.services import diagram_draft_service


# ── Fixture ────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _patch_drafts_path(tmp_path: Path, monkeypatch):
    """Redireciona o caminho de drafts para pasta temporária em cada teste."""
    import app.services.diagram_draft_service as svc

    mock_settings = type("S", (), {"drafts_path": tmp_path / "drafts"})()
    monkeypatch.setattr(svc, "settings", mock_settings)


def _make_request(name: str = "nova_tabela") -> AddDraftTableRequest:
    return AddDraftTableRequest(
        name=name,
        columns=[
            DraftColumn(name="id", sql_type="INT", pk=True, auto_increment=True, nullable=False),
            DraftColumn(name="descricao", sql_type="VARCHAR(255)"),
        ],
    )


# ── Testes ─────────────────────────────────────────────────────────────────────

def test_get_draft_returns_empty_when_no_file():
    result = diagram_draft_service.get_draft("agent-x")
    assert isinstance(result, DiagramDraft)
    assert result.agent_id == "agent-x"
    assert result.draft_tables == []


def test_add_table_persists_draft():
    req = _make_request("Pedido")
    table = diagram_draft_service.add_table("agent1", req)

    assert isinstance(table, DraftTable)
    assert table.name == "Pedido"
    assert len(table.columns) == 2

    draft = diagram_draft_service.get_draft("agent1")
    assert len(draft.draft_tables) == 1
    assert draft.draft_tables[0].name == "Pedido"


def test_add_table_replaces_existing_with_same_name():
    diagram_draft_service.add_table("agent2", _make_request("Tab"))

    updated = AddDraftTableRequest(
        name="Tab",
        columns=[DraftColumn(name="novo_campo", sql_type="TEXT")],
    )
    diagram_draft_service.add_table("agent2", updated)

    draft = diagram_draft_service.get_draft("agent2")
    assert len(draft.draft_tables) == 1
    assert draft.draft_tables[0].columns[0].name == "novo_campo"


def test_add_multiple_tables():
    diagram_draft_service.add_table("agent3", _make_request("TabA"))
    diagram_draft_service.add_table("agent3", _make_request("TabB"))
    diagram_draft_service.add_table("agent3", _make_request("TabC"))

    draft = diagram_draft_service.get_draft("agent3")
    names = {t.name for t in draft.draft_tables}
    assert names == {"TabA", "TabB", "TabC"}


def test_remove_table_returns_true_when_found():
    diagram_draft_service.add_table("agent4", _make_request("Remover"))
    removed = diagram_draft_service.remove_table("agent4", "Remover")

    assert removed is True
    draft = diagram_draft_service.get_draft("agent4")
    assert draft.draft_tables == []


def test_remove_table_returns_false_when_not_found():
    diagram_draft_service.add_table("agent5", _make_request("Existe"))
    removed = diagram_draft_service.remove_table("agent5", "NaoExiste")

    assert removed is False
    draft = diagram_draft_service.get_draft("agent5")
    assert len(draft.draft_tables) == 1


def test_promote_table_removes_draft():
    diagram_draft_service.add_table("agent6", _make_request("Promover"))
    result = diagram_draft_service.promote_table("agent6", "Promover")

    assert result is True
    draft = diagram_draft_service.get_draft("agent6")
    assert draft.draft_tables == []


def test_clear_all_removes_file(tmp_path):
    import app.services.diagram_draft_service as svc
    # garantir que o diretório existe (criado via fixture)
    diagram_draft_service.add_table("agent7", _make_request("AQualquer"))
    diagram_draft_service.clear_all("agent7")

    # Após clear, get_draft deve retornar vazio de novo
    draft = diagram_draft_service.get_draft("agent7")
    assert draft.draft_tables == []


def test_draft_columns_preserved_correctly():
    req = AddDraftTableRequest(
        name="Detalhada",
        columns=[
            DraftColumn(name="id", sql_type="BIGINT UNSIGNED", pk=True,
                        auto_increment=True, nullable=False),
            DraftColumn(name="nome", sql_type="VARCHAR(200)", nullable=False,
                        default_val="'sem_nome'"),
            DraftColumn(name="ativo", sql_type="TINYINT(1)", nullable=True,
                        default_val="1"),
        ],
    )
    diagram_draft_service.add_table("agent8", req)
    draft = diagram_draft_service.get_draft("agent8")

    cols = draft.draft_tables[0].columns
    assert len(cols) == 3
    assert cols[0].name == "id"
    assert cols[0].pk is True
    assert cols[0].auto_increment is True
    assert cols[1].default_val == "'sem_nome'"
    assert cols[2].nullable is True
