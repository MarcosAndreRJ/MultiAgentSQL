"""
Testes do diagram_service.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch

import pytest

from app.schemas.digest import (
    ColumnInfo,
    DBDigest,
    DigestSummary,
    ForeignKeyInfo,
    TableDigest,
)
from app.services.diagram_service import (
    DiagramDigestInvalidError,
    DiagramDigestNotFoundError,
    build_diagram,
    get_diagram_status,
)


def _write_digest(tmp_path, digest: DBDigest, agent_id: str = "ag-diagram") -> None:
    out = tmp_path / f"{agent_id}.digest.json"
    out.write_text(digest.model_dump_json(indent=2), encoding="utf-8")


@pytest.fixture
def diagram_tmp_dir():
    base = Path.cwd() / "data" / "test-digests-diagram"
    base.mkdir(parents=True, exist_ok=True)
    temp_dir = base / f"case-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_build_diagram_transforms_digest_to_nodes_and_edges(diagram_tmp_dir):
    digest = DBDigest(
        agent_id="ag-diagram",
        database="db_x",
        summary=DigestSummary(tables=2, views=1),
        tables=[
            TableDigest(
                name="users",
                type="BASE TABLE",
                primary_key="id",
                columns=[
                    ColumnInfo(name="id", type="int", nullable=False),
                    ColumnInfo(name="name", type="varchar(100)", nullable=False),
                ],
            ),
            TableDigest(
                name="orders",
                type="BASE TABLE",
                primary_key="id",
                columns=[
                    ColumnInfo(name="id", type="int", nullable=False),
                    ColumnInfo(name="user_id", type="int", nullable=False),
                ],
                foreign_keys=[
                    ForeignKeyInfo(
                        constraint_name="fk_orders_user",
                        column="user_id",
                        ref_table="users",
                        ref_column="id",
                    )
                ],
                related_tables=["users"],
            ),
        ],
        views=[
            TableDigest(
                name="vw_orders",
                type="VIEW",
                columns=[ColumnInfo(name="id", type="int", nullable=False)],
            )
        ],
    )

    _write_digest(diagram_tmp_dir, digest)

    with patch("app.services.diagram_service.settings") as mocked_settings:
        mocked_settings.digests_path = diagram_tmp_dir
        payload = build_diagram("ag-diagram", agent_name="Agent Diagram")

    assert payload.agent_name == "Agent Diagram"
    assert payload.database == "db_x"
    assert payload.summary.nodes == 3
    assert payload.summary.edges == 1

    orders_node = next(node for node in payload.nodes if node.id == "orders")
    assert orders_node.primary_key == ["id"]
    assert any(column.name == "id" and column.is_pk for column in orders_node.columns)
    assert any(column.name == "user_id" and column.is_fk for column in orders_node.columns)

    edge = payload.edges[0]
    assert edge.source == "orders"
    assert edge.target == "users"
    assert edge.fk_column == "user_id"
    assert edge.relation_type == "foreign_key"


def test_build_diagram_uses_related_tables_when_no_fk(diagram_tmp_dir):
    """
    Digest com apenas related_tables (heurístico) e sem FKs reais:
    o novo pipeline não gera edges para related_tables — apenas para FKs explícitas.
    Este comportamento é intencional: o diagrama só exibe relacionamentos reais do banco.
    """
    digest = DBDigest(
        agent_id="ag-diagram",
        database="db_x",
        summary=DigestSummary(tables=2),
        tables=[
            TableDigest(name="A", type="BASE TABLE", columns=[ColumnInfo(name="id", type="int")], related_tables=["B"]),
            TableDigest(name="B", type="BASE TABLE", columns=[ColumnInfo(name="id", type="int")], related_tables=["A"]),
        ],
    )
    _write_digest(diagram_tmp_dir, digest)

    with patch("app.services.diagram_service.settings") as mocked_settings:
        mocked_settings.digests_path = diagram_tmp_dir
        payload = build_diagram("ag-diagram")

    # related_tables heurísticos não geram edges — apenas FKs explícitas geram
    assert payload.summary.edges == 0
    assert payload.edges == []


def test_build_diagram_without_relationships(diagram_tmp_dir):
    digest = DBDigest(
        agent_id="ag-diagram",
        database="db_x",
        summary=DigestSummary(tables=1),
        tables=[
            TableDigest(
                name="standalone",
                type="BASE TABLE",
                columns=[ColumnInfo(name="id", type="int", nullable=False)],
            )
        ],
    )
    _write_digest(diagram_tmp_dir, digest)

    with patch("app.services.diagram_service.settings") as mocked_settings:
        mocked_settings.digests_path = diagram_tmp_dir
        payload = build_diagram("ag-diagram")

    assert payload.summary.nodes == 1
    assert payload.edges == []


def test_build_diagram_when_missing_digest_raises(diagram_tmp_dir):
    with patch("app.services.diagram_service.settings") as mocked_settings:
        mocked_settings.digests_path = diagram_tmp_dir
        with pytest.raises(DiagramDigestNotFoundError):
            build_diagram("missing-agent")


def test_build_diagram_when_digest_invalid_raises(diagram_tmp_dir):
    out = diagram_tmp_dir / "ag-diagram.digest.json"
    out.write_text("{ this is not json", encoding="utf-8")

    with patch("app.services.diagram_service.settings") as mocked_settings:
        mocked_settings.digests_path = diagram_tmp_dir
        with pytest.raises(DiagramDigestInvalidError):
            build_diagram("ag-diagram")


def test_get_diagram_status_for_missing_and_valid_digest(diagram_tmp_dir):
    with patch("app.services.diagram_service.settings") as mocked_settings:
        mocked_settings.digests_path = diagram_tmp_dir

        missing = get_diagram_status("ghost")
        assert missing.exists is False
        assert missing.valid is False

        digest = DBDigest(
            agent_id="ag-diagram",
            database="db_status",
            summary=DigestSummary(tables=1),
            tables=[TableDigest(name="t", type="BASE TABLE", columns=[ColumnInfo(name="id", type="int")])],
        )
        _write_digest(diagram_tmp_dir, digest)

        status = get_diagram_status("ag-diagram")
        assert status.exists is True
        assert status.valid is True
        assert status.database == "db_status"
        assert status.nodes == 1
