"""
Tests: _build_relationships em digest_service

Verifica que o pipeline de coleta de relacionamentos:
- detecta FKs reais como RelationshipInfo
- deduplica FKs repetidas
- ignora referências a tabelas fora do digest
- retorna lista vazia quando não há FKs
"""
import pytest

from app.schemas.digest import ForeignKeyInfo, RelationshipInfo, TableDigest
from app.services.digest_service import _build_relationships


def _make_table(name: str, fks: list[dict] | None = None) -> TableDigest:
    fks = fks or []
    return TableDigest(
        name=name,
        type="BASE TABLE",
        foreign_keys=[ForeignKeyInfo(**fk) for fk in fks],
    )


# ── Casos básicos ──────────────────────────────────────────────────────────────

def test_single_fk_detected():
    tables = [
        _make_table("Pedido", [
            dict(constraint_name="fk_pedido_cliente", column="idCliente",
                 ref_table="Cliente", ref_column="idCliente"),
        ]),
        _make_table("Cliente"),
    ]
    table_names = {t.name for t in tables}
    rels = _build_relationships(tables, table_names)

    assert len(rels) == 1
    r = rels[0]
    assert isinstance(r, RelationshipInfo)
    assert r.source_table == "Pedido"
    assert r.source_column == "idCliente"
    assert r.target_table == "Cliente"
    assert r.target_column == "idCliente"
    assert r.constraint_name == "fk_pedido_cliente"
    assert r.relationship_type == "many-to-one"


def test_multiple_fks_on_same_table():
    tables = [
        _make_table("ItemPedido", [
            dict(constraint_name="fk_item_pedido", column="idPedido",
                 ref_table="Pedido", ref_column="idPedido"),
            dict(constraint_name="fk_item_produto", column="idProduto",
                 ref_table="Produto", ref_column="idProduto"),
        ]),
        _make_table("Pedido"),
        _make_table("Produto"),
    ]
    table_names = {t.name for t in tables}
    rels = _build_relationships(tables, table_names)

    assert len(rels) == 2
    targets = {r.target_table for r in rels}
    assert targets == {"Pedido", "Produto"}


def test_fk_referencing_table_outside_digest_is_ignored():
    """FK para tabela que não está no digest deve ser ignorada."""
    tables = [
        _make_table("Pedido", [
            dict(constraint_name="fk_int", column="idExterno",
                 ref_table="TabelaExterna", ref_column="id"),
        ]),
    ]
    table_names = {"Pedido"}  # TabelaExterna não está aqui
    rels = _build_relationships(tables, table_names)

    assert len(rels) == 0


def test_no_fks_returns_empty():
    tables = [
        _make_table("Produto"),
        _make_table("Categoria"),
    ]
    table_names = {t.name for t in tables}
    rels = _build_relationships(tables, table_names)

    assert rels == []


def test_duplicate_fk_is_deduplicated():
    """Duas entradas idênticas de FK no mesmo par devem gerar apenas 1 RelationshipInfo."""
    fk = dict(constraint_name="fk_dup", column="idRef", ref_table="Ref", ref_column="id")
    tables = [
        _make_table("TabA", [fk, fk]),  # FK duplicada na mesma tabela
        _make_table("Ref"),
    ]
    table_names = {t.name for t in tables}
    rels = _build_relationships(tables, table_names)

    assert len(rels) == 1


def test_same_fk_on_two_different_tables_counts_separately():
    """Mesmo par (col → ref) em tabelas diferentes = 2 relacionamentos distintos."""
    fk = dict(constraint_name="fk_shared", column="idOwner", ref_table="Owner", ref_column="id")
    tables = [
        _make_table("TabA", [fk]),
        _make_table("TabB", [fk]),
        _make_table("Owner"),
    ]
    table_names = {t.name for t in tables}
    rels = _build_relationships(tables, table_names)

    assert len(rels) == 2
    sources = {r.source_table for r in rels}
    assert sources == {"TabA", "TabB"}


def test_empty_tables_list():
    rels = _build_relationships([], set())
    assert rels == []
