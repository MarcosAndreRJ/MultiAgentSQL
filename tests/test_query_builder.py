"""
Testes unitários para app/services/query_builder.py
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
from app.services.filter_parser import QueryFilter, OrderByClause
from app.services.join_resolver import JoinPath
from app.services.query_builder import V2Plan, build_sql, _HARD_MAX_LIMIT, _DEFAULT_LIMIT


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _col(name: str, typ: str = "varchar") -> ColumnInfo:
    return ColumnInfo(name=name, type=typ)


def _fk(col: str, ref_table: str, ref_col: str) -> ForeignKeyInfo:
    return ForeignKeyInfo(constraint_name=f"fk_{col}", column=col, ref_table=ref_table, ref_column=ref_col)


def _make_digest(tables: list[TableDigest]) -> DBDigest:
    return DBDigest(
        agent_id="test-agent",
        database="test_db",
        generated_at=datetime(2024, 1, 1),
        summary=DigestSummary(tables=len(tables)),
        tables=tables,
        views=[],
    )


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def simple_digest():
    clientes = TableDigest(
        name="clientes",
        columns=[_col("id", "int"), _col("nome"), _col("status"), _col("cidade")],
        foreign_keys=[],
    )
    return _make_digest([clientes])


@pytest.fixture
def join_digest():
    clientes = TableDigest(
        name="clientes",
        columns=[_col("id", "int"), _col("nome"), _col("status")],
        foreign_keys=[],
    )
    pedidos = TableDigest(
        name="pedidos",
        columns=[_col("id", "int"), _col("cliente_id", "int"), _col("total", "decimal"), _col("status")],
        foreign_keys=[_fk("cliente_id", "clientes", "id")],
    )
    return _make_digest([clientes, pedidos])


# ─── SELECT simples ───────────────────────────────────────────────────────────

class TestBuildSelectSimple:
    def test_basic_select(self, simple_digest):
        plan = V2Plan(intent="SELECT", tables=["clientes"])
        r = build_sql(plan, simple_digest)
        assert r is not None
        assert "SELECT *" in r.sql
        assert "`clientes`" in r.sql
        assert f"LIMIT {_DEFAULT_LIMIT}" in r.sql
        assert r.params == {}

    def test_select_with_limit(self, simple_digest):
        plan = V2Plan(intent="SELECT", tables=["clientes"], limit=10)
        r = build_sql(plan, simple_digest)
        assert "LIMIT 10" in r.sql

    def test_limit_capped_at_hard_max(self, simple_digest):
        plan = V2Plan(intent="SELECT", tables=["clientes"], limit=99999)
        r = build_sql(plan, simple_digest)
        assert f"LIMIT {_HARD_MAX_LIMIT}" in r.sql

    def test_select_with_filter(self, simple_digest):
        plan = V2Plan(
            intent="SELECT",
            tables=["clientes"],
            filters=[QueryFilter(field="status", op="=", value="ativo")],
        )
        r = build_sql(plan, simple_digest)
        assert r is not None
        assert "WHERE" in r.sql
        assert "`status` = %(p0)s" in r.sql
        assert list(r.params.values()) == ["ativo"]

    def test_select_with_like_filter(self, simple_digest):
        plan = V2Plan(
            intent="SELECT",
            tables=["clientes"],
            filters=[QueryFilter(field="nome", op="LIKE", value="%joao%")],
        )
        r = build_sql(plan, simple_digest)
        assert "LIKE %(p0)s" in r.sql
        assert list(r.params.values()) == ["%joao%"]

    def test_select_filter_unknown_column_ignored(self, simple_digest):
        """Filtro em coluna inexistente deve ser ignorado (não gerar WHERE inválido)."""
        plan = V2Plan(
            intent="SELECT",
            tables=["clientes"],
            filters=[QueryFilter(field="coluna_inexistente", op="=", value="x")],
        )
        r = build_sql(plan, simple_digest)
        assert r is not None
        assert "WHERE" not in r.sql  # filtro ignorado

    def test_select_with_order_by(self, simple_digest):
        plan = V2Plan(
            intent="SELECT",
            tables=["clientes"],
            order_by=[OrderByClause(field="nome", direction="asc")],
        )
        r = build_sql(plan, simple_digest)
        assert "ORDER BY" in r.sql
        assert "`nome` ASC" in r.sql

    def test_select_order_by_unknown_column_ignored(self, simple_digest):
        plan = V2Plan(
            intent="SELECT",
            tables=["clientes"],
            order_by=[OrderByClause(field="coluna_fake")],
        )
        r = build_sql(plan, simple_digest)
        assert "ORDER BY" not in r.sql

    def test_select_order_by_desc(self, simple_digest):
        plan = V2Plan(
            intent="SELECT",
            tables=["clientes"],
            order_by=[OrderByClause(field="id", direction="desc")],
        )
        r = build_sql(plan, simple_digest)
        assert "`id` DESC" in r.sql

    def test_tables_used(self, simple_digest):
        plan = V2Plan(intent="SELECT", tables=["clientes"])
        r = build_sql(plan, simple_digest)
        assert r.tables_used == ["clientes"]

    def test_is_null_filter(self, simple_digest):
        plan = V2Plan(
            intent="SELECT",
            tables=["clientes"],
            filters=[QueryFilter(field="cidade", op="IS NULL", value=None)],
        )
        r = build_sql(plan, simple_digest)
        assert "IS NULL" in r.sql
        assert r.params == {}

    def test_is_not_null_filter(self, simple_digest):
        plan = V2Plan(
            intent="SELECT",
            tables=["clientes"],
            filters=[QueryFilter(field="cidade", op="IS NOT NULL", value=None)],
        )
        r = build_sql(plan, simple_digest)
        assert "IS NOT NULL" in r.sql


# ─── COUNT ────────────────────────────────────────────────────────────────────

class TestBuildCount:
    def test_basic_count(self, simple_digest):
        plan = V2Plan(intent="COUNT", tables=["clientes"])
        r = build_sql(plan, simple_digest)
        assert r is not None
        assert "COUNT(*) AS total" in r.sql
        assert "LIMIT" not in r.sql  # COUNT não tem LIMIT

    def test_count_with_filter(self, simple_digest):
        plan = V2Plan(
            intent="COUNT",
            tables=["clientes"],
            filters=[QueryFilter(field="status", op="=", value="inativo")],
        )
        r = build_sql(plan, simple_digest)
        assert "WHERE" in r.sql
        assert list(r.params.values()) == ["inativo"]


# ─── SELECT JOIN ──────────────────────────────────────────────────────────────

class TestBuildSelectJoin:
    def _make_jp(self) -> JoinPath:
        return JoinPath(
            left_table="pedidos",
            right_table="clientes",
            left_col="cliente_id",
            right_col="id",
            direction="direct",
            confidence=1.0,
        )

    def test_basic_join(self, join_digest):
        jp = self._make_jp()
        plan = V2Plan(
            intent="SELECT_JOIN",
            tables=["pedidos", "clientes"],
            join_path=jp,
        )
        r = build_sql(plan, join_digest)
        assert r is not None
        assert "INNER JOIN" in r.sql
        assert "`pedidos`" in r.sql
        assert "`clientes`" in r.sql
        assert "`pedidos`.`cliente_id` = `clientes`.`id`" in r.sql
        assert r.tables_used == ["pedidos", "clientes"]

    def test_join_with_filter(self, join_digest):
        jp = self._make_jp()
        plan = V2Plan(
            intent="SELECT_JOIN",
            tables=["pedidos", "clientes"],
            join_path=jp,
            filters=[QueryFilter(field="status", op="=", value="pago")],
        )
        r = build_sql(plan, join_digest)
        assert "WHERE" in r.sql
        assert list(r.params.values()) == ["pago"]

    def test_join_without_join_path_returns_none(self, join_digest):
        plan = V2Plan(
            intent="SELECT_JOIN",
            tables=["pedidos", "clientes"],
            join_path=None,
        )
        r = build_sql(plan, join_digest)
        assert r is None

    def test_count_join(self, join_digest):
        jp = self._make_jp()
        plan = V2Plan(
            intent="COUNT_JOIN",
            tables=["pedidos", "clientes"],
            join_path=jp,
        )
        r = build_sql(plan, join_digest)
        assert r is not None
        assert "COUNT(*)" in r.sql
        assert "INNER JOIN" in r.sql
        assert "LIMIT" not in r.sql


# ─── Casos de recusa ──────────────────────────────────────────────────────────

class TestBuildRefusal:
    def test_low_confidence_returns_none(self, simple_digest):
        plan = V2Plan(intent="SELECT", tables=["clientes"], confidence=0.5)
        assert build_sql(plan, simple_digest) is None

    def test_unknown_table_returns_none(self, simple_digest):
        plan = V2Plan(intent="SELECT", tables=["tabela_inexistente"])
        assert build_sql(plan, simple_digest) is None

    def test_unknown_intent_returns_none(self, simple_digest):
        plan = V2Plan(intent="INSERT", tables=["clientes"])
        assert build_sql(plan, simple_digest) is None

    def test_to_dict(self, simple_digest):
        plan = V2Plan(intent="COUNT", tables=["clientes"])
        r = build_sql(plan, simple_digest)
        d = r.to_dict()
        assert "sql" in d
        assert "params" in d
        assert "tables_used" in d


# ─── Segurança: nomes com backtick ───────────────────────────────────────────

class TestSQLInjectionPrevention:
    def test_table_name_backtick_escaped(self, simple_digest):
        plan = V2Plan(intent="SELECT", tables=["clientes"])
        r = build_sql(plan, simple_digest)
        assert "`clientes`" in r.sql

    def test_column_name_backtick_escaped(self, simple_digest):
        plan = V2Plan(
            intent="SELECT",
            tables=["clientes"],
            filters=[QueryFilter(field="status", op="=", value="ativo")],
        )
        r = build_sql(plan, simple_digest)
        assert "`status`" in r.sql

    def test_value_not_in_sql(self, simple_digest):
        """O valor do filtro nunca deve aparecer diretamente no SQL."""
        plan = V2Plan(
            intent="SELECT",
            tables=["clientes"],
            filters=[QueryFilter(field="nome", op="=", value="'; DROP TABLE clientes; --")],
        )
        r = build_sql(plan, simple_digest)
        if r is not None:
            assert "DROP" not in r.sql
            assert list(r.params.values()) == ["'; DROP TABLE clientes; --"]
