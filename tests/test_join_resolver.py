"""
Testes unitários para app/services/join_resolver.py
"""
import pytest
from datetime import datetime

from app.schemas.digest import (
    DBDigest,
    DigestSummary,
    TableDigest,
    ColumnInfo,
    ForeignKeyInfo,
)
from app.services.join_resolver import (
    resolve_join,
    find_join_chain,
    table_exists_in_digest,
    get_table_from_digest,
    JoinPath,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def _make_digest(tables: list[TableDigest]) -> DBDigest:
    return DBDigest(
        agent_id="test-agent",
        database="test_db",
        generated_at=datetime(2024, 1, 1),
        summary=DigestSummary(tables=len(tables)),
        tables=tables,
        views=[],
    )


def _col(name: str, typ: str = "varchar") -> ColumnInfo:
    return ColumnInfo(name=name, type=typ)


def _fk(col: str, ref_table: str, ref_col: str) -> ForeignKeyInfo:
    return ForeignKeyInfo(
        constraint_name=f"fk_{col}",
        column=col,
        ref_table=ref_table,
        ref_column=ref_col,
    )


# ─── Fixtures de digest ───────────────────────────────────────────────────────

@pytest.fixture
def simple_digest():
    """Digest com Pedido → Cliente via pedido.cliente_id → clientes.id"""
    clientes = TableDigest(
        name="clientes",
        columns=[_col("id", "int"), _col("nome"), _col("email")],
        foreign_keys=[],
    )
    pedidos = TableDigest(
        name="pedidos",
        columns=[_col("id", "int"), _col("cliente_id", "int"), _col("total", "decimal")],
        foreign_keys=[_fk("cliente_id", "clientes", "id")],
    )
    return _make_digest([clientes, pedidos])


@pytest.fixture
def ambiguous_digest():
    """Digest com dois FKs de pedidos → clientes (ambíguo)."""
    clientes = TableDigest(name="clientes", columns=[_col("id")], foreign_keys=[])
    pedidos = TableDigest(
        name="pedidos",
        columns=[_col("id"), _col("cliente_id"), _col("vendedor_id")],
        foreign_keys=[
            _fk("cliente_id", "clientes", "id"),
            _fk("vendedor_id", "clientes", "id"),
        ],
    )
    return _make_digest([clientes, pedidos])


@pytest.fixture
def chain_digest():
    """Pedidos → itens → produtos (cadeia de 3 tabelas)."""
    pedidos = TableDigest(name="pedidos", columns=[_col("id")], foreign_keys=[])
    itens = TableDigest(
        name="itens",
        columns=[_col("id"), _col("pedido_id"), _col("produto_id")],
        foreign_keys=[
            _fk("pedido_id", "pedidos", "id"),
            _fk("produto_id", "produtos", "id"),
        ],
    )
    produtos = TableDigest(name="produtos", columns=[_col("id"), _col("nome")], foreign_keys=[])
    return _make_digest([pedidos, itens, produtos])


# ─── resolve_join: caminho direto ─────────────────────────────────────────────

class TestResolveJoin:
    def test_direct_fk(self, simple_digest):
        jp = resolve_join(simple_digest, "pedidos", "clientes")
        assert jp is not None
        assert jp.left_table == "pedidos"
        assert jp.right_table == "clientes"
        assert jp.left_col == "cliente_id"
        assert jp.right_col == "id"
        assert jp.direction == "direct"
        assert jp.confidence == 1.0

    def test_reverse_fk(self, simple_digest):
        """Chamar com a ordem invertida deve achar a FK reversa."""
        jp = resolve_join(simple_digest, "clientes", "pedidos")
        assert jp is not None
        assert jp.direction == "reverse"
        assert jp.left_col == "id"
        assert jp.right_col == "cliente_id"

    def test_no_fk(self, simple_digest):
        """Duas tabelas sem FK entre si → None."""
        outra = TableDigest(name="produtos", columns=[_col("id")], foreign_keys=[])
        digest = _make_digest(list(simple_digest.tables) + [outra])
        assert resolve_join(digest, "clientes", "produtos") is None

    def test_table_not_in_digest(self, simple_digest):
        assert resolve_join(simple_digest, "pedidos", "inexistente") is None
        assert resolve_join(simple_digest, "inexistente", "clientes") is None

    def test_ambiguous_fks(self, ambiguous_digest):
        """Múltiplos caminhos → None (ambíguo)."""
        assert resolve_join(ambiguous_digest, "pedidos", "clientes") is None

    def test_case_insensitive(self, simple_digest):
        jp = resolve_join(simple_digest, "PEDIDOS", "CLIENTES")
        assert jp is not None

    def test_to_dict(self, simple_digest):
        jp = resolve_join(simple_digest, "pedidos", "clientes")
        d = jp.to_dict()
        assert d["left_table"] == "pedidos"
        assert d["confidence"] == 1.0


# ─── find_join_chain ─────────────────────────────────────────────────────────

class TestFindJoinChain:
    def test_two_tables(self, simple_digest):
        chain = find_join_chain(simple_digest, ["pedidos", "clientes"])
        assert chain is not None
        assert len(chain) == 1

    def test_three_tables_chain(self, chain_digest):
        chain = find_join_chain(chain_digest, ["pedidos", "itens", "produtos"])
        assert chain is not None
        assert len(chain) == 2
        assert chain[0].left_table == "pedidos"
        assert chain[1].right_table == "produtos"

    def test_single_table(self, simple_digest):
        chain = find_join_chain(simple_digest, ["pedidos"])
        assert chain == []

    def test_broken_chain(self, simple_digest):
        """Se algum par não tem FK, retorna None."""
        chain = find_join_chain(simple_digest, ["pedidos", "clientes", "inexistente"])
        assert chain is None

    def test_empty_list(self, simple_digest):
        chain = find_join_chain(simple_digest, [])
        assert chain == []


# ─── table_exists_in_digest / get_table_from_digest ──────────────────────────

class TestHelpers:
    def test_table_exists_true(self, simple_digest):
        assert table_exists_in_digest(simple_digest, "clientes") is True
        assert table_exists_in_digest(simple_digest, "CLIENTES") is True

    def test_table_exists_false(self, simple_digest):
        assert table_exists_in_digest(simple_digest, "inexistente") is False

    def test_get_table(self, simple_digest):
        td = get_table_from_digest(simple_digest, "pedidos")
        assert td is not None
        assert td.name == "pedidos"
        assert len(td.columns) == 3

    def test_get_table_none(self, simple_digest):
        assert get_table_from_digest(simple_digest, "xxx") is None

    def test_view_in_digest(self):
        """Views também devem ser encontradas."""
        from app.schemas.digest import TableDigest
        view = TableDigest(name="vw_resumo", type="VIEW", columns=[_col("id")])
        digest = DBDigest(
            agent_id="a",
            database="d",
            tables=[],
            views=[view],
        )
        assert table_exists_in_digest(digest, "vw_resumo") is True
        td = get_table_from_digest(digest, "vw_resumo")
        assert td.type == "VIEW"
