"""
Tests: build_diagram → edges corretos

Verifica que:
- edges vêm de digest.relationships (canônico)
- fallback legacy usa FKs por tabela quando relationships=[]
- edges têm IDs estáveis
- draft nodes não geram edges
- tabela sem par no digest não gera edge
"""
import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from app.schemas.digest import (
    DBDigest,
    DigestSummary,
    ForeignKeyInfo,
    RelationshipInfo,
    TableDigest,
)
from app.schemas.diagram import DiagramEdge
from app.services.diagram_service import (
    DiagramDigestNotFoundError,
    _build_node_from_table,
    build_diagram,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_digest(
    agent_id: str = "agent-test",
    tables: list[TableDigest] | None = None,
    relationships: list[RelationshipInfo] | None = None,
) -> DBDigest:
    tables = tables or []
    return DBDigest(
        agent_id=agent_id,
        database="test_db",
        generated_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        summary=DigestSummary(
            tables=len(tables),
            relationships=len(relationships or []),
        ),
        tables=tables,
        relationships=relationships or [],
    )


def _persist_digest(tmp_path: Path, digest: DBDigest) -> Path:
    digests_dir = tmp_path / "digests"
    digests_dir.mkdir(parents=True, exist_ok=True)
    out = digests_dir / f"{digest.agent_id}.digest.json"
    out.write_text(digest.model_dump_json(), encoding="utf-8")
    return out


def _patch_paths(tmp_path: Path):
    """Patcher de contexto para redirecionar settings.digests_path e data_path."""
    from unittest.mock import MagicMock
    import app.services.diagram_service as svc

    mock_settings = MagicMock()
    mock_settings.digests_path = tmp_path / "digests"
    mock_settings.data_path = tmp_path

    return patch.object(svc, "settings", mock_settings)


# ── Testes principais ──────────────────────────────────────────────────────────

def test_edges_come_from_relationships(tmp_path):
    """Quando digest tem relationships, build_diagram usa esses para criar edges."""
    tables = [
        TableDigest(name="Pedido", type="BASE TABLE",
                    foreign_keys=[ForeignKeyInfo(constraint_name="fk",
                                                  column="idCliente",
                                                  ref_table="Cliente",
                                                  ref_column="idCliente")]),
        TableDigest(name="Cliente", type="BASE TABLE"),
    ]
    rels = [
        RelationshipInfo(
            source_table="Pedido", source_column="idCliente",
            target_table="Cliente", target_column="idCliente",
            constraint_name="fk",
        )
    ]
    digest = _make_digest(tables=tables, relationships=rels)
    _persist_digest(tmp_path, digest)

    with _patch_paths(tmp_path):
        payload = build_diagram("agent-test")

    assert len(payload.edges) == 1
    edge = payload.edges[0]
    assert edge.source == "Pedido"
    assert edge.target == "Cliente"
    assert edge.fk_column == "idCliente"


def test_legacy_digest_falls_back_to_per_table_fks(tmp_path):
    """Digest sem relationships (legado) → edges derivados das FKs por tabela."""
    tables = [
        TableDigest(name="Pedido", type="BASE TABLE",
                    foreign_keys=[ForeignKeyInfo(constraint_name="fk_leg",
                                                  column="idCliente",
                                                  ref_table="Cliente",
                                                  ref_column="id")]),
        TableDigest(name="Cliente", type="BASE TABLE"),
    ]
    digest = _make_digest(tables=tables, relationships=[])  # sem relationships
    _persist_digest(tmp_path, digest)

    with _patch_paths(tmp_path):
        payload = build_diagram("agent-test")

    assert len(payload.edges) == 1
    edge = payload.edges[0]
    assert edge.source == "Pedido"
    assert edge.target == "Cliente"


def test_no_edge_when_ref_table_missing_from_diagram(tmp_path):
    """FK para tabela não presente no digest não gera edge."""
    rels = [
        RelationshipInfo(
            source_table="Pedido", source_column="idExt",
            target_table="TabelaExterna", target_column="id",
            constraint_name="fk_ext",
        )
    ]
    tables = [TableDigest(name="Pedido", type="BASE TABLE")]
    digest = _make_digest(tables=tables, relationships=rels)
    _persist_digest(tmp_path, digest)

    with _patch_paths(tmp_path):
        payload = build_diagram("agent-test")

    assert len(payload.edges) == 0


def test_edge_ids_are_stable(tmp_path):
    """Edge IDs são determinísticos e não variam entre chamadas."""
    rels = [
        RelationshipInfo(
            source_table="A", source_column="idB",
            target_table="B", target_column="id",
            constraint_name="fk_a_b",
        )
    ]
    tables = [TableDigest(name="A"), TableDigest(name="B")]
    digest = _make_digest(tables=tables, relationships=rels)
    _persist_digest(tmp_path, digest)

    with _patch_paths(tmp_path):
        p1 = build_diagram("agent-test")
    _persist_digest(tmp_path, digest)  # re-persist (sem mudança)
    with _patch_paths(tmp_path):
        p2 = build_diagram("agent-test")

    ids1 = {e.id for e in p1.edges}
    ids2 = {e.id for e in p2.edges}
    assert ids1 == ids2


def test_no_edges_when_no_relationships_and_no_fks(tmp_path):
    tables = [TableDigest(name="A"), TableDigest(name="B")]
    digest = _make_digest(tables=tables, relationships=[])
    _persist_digest(tmp_path, digest)

    with _patch_paths(tmp_path):
        payload = build_diagram("agent-test")

    assert payload.edges == []


def test_duplicate_relationships_produce_single_edge(tmp_path):
    """Relacionamentos duplicados no digest não devem gerar edges duplicadas."""
    rel = RelationshipInfo(
        source_table="A", source_column="idB",
        target_table="B", target_column="id",
        constraint_name="fk_dup",
    )
    tables = [TableDigest(name="A"), TableDigest(name="B")]
    digest = _make_digest(tables=tables, relationships=[rel, rel])
    _persist_digest(tmp_path, digest)

    with _patch_paths(tmp_path):
        payload = build_diagram("agent-test")

    assert len(payload.edges) == 1


def test_raises_when_digest_not_found(tmp_path):
    (tmp_path / "digests").mkdir(parents=True)

    with _patch_paths(tmp_path):
        with pytest.raises(DiagramDigestNotFoundError):
            build_diagram("inexistente")
