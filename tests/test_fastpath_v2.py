"""
Testes de integração para app/services/fastpath_v2_service.py.

Usa mocks para:
- digest_service.load_digest  → retorna digest fabricado
- alias_service (via fastpath_v2_service) → resolve_message_aliases
- db_execute.execute          → retorna resultado fictício

Não requer conexão real com banco de dados.
"""
from __future__ import annotations

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.agent import AgentConfig, DatabaseConfig, AgentBehavior
from app.schemas.chat import Session
from app.schemas.digest import (
    DBDigest,
    DigestSummary,
    TableDigest,
    ColumnInfo,
    ForeignKeyInfo,
)
from app.schemas.execution import DBExecuteResult
from app.services import fastpath_v2_service


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


def _make_agent(agent_id: str = "test-agent") -> AgentConfig:
    return AgentConfig(
        id=agent_id,
        name="Test Agent",
        description="Agente de teste",
        type="mysql-specialist",
        model="llama3",
        prompt_file="config/prompts/mysql-specialist.md",
        database=DatabaseConfig(
            host="localhost",
            port=3306,
            name="test_db",
            user="root",
            password="",
        ),
        behavior=AgentBehavior(max_loop_steps=3),
    )


def _make_session() -> Session:
    return Session(session_id="sess-001", agent_id="test-agent", messages=[])


def _ok_result(rows: list[dict], columns: list[str] | None = None) -> DBExecuteResult:
    cols = columns or (list(rows[0].keys()) if rows else [])
    return DBExecuteResult(
        success=True,
        rows=rows,
        rows_affected=len(rows),
        columns=cols,
        execution_time_ms=1.0,
        sql_executed="SELECT ...",
        error=None,
        truncated=False,
    )


# ─── Fixture de digest ────────────────────────────────────────────────────────

@pytest.fixture
def digest_clientes():
    clientes = TableDigest(
        name="clientes",
        columns=[
            _col("id", "int"),
            _col("nome"),
            _col("status"),
            _col("cidade"),
            _col("email"),
        ],
        foreign_keys=[],
    )
    return _make_digest([clientes])


@pytest.fixture
def digest_com_join():
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


# ─── Helpers de mock ──────────────────────────────────────────────────────────

def _patch_all(digest, exec_rows: list[dict], exec_cols: list[str] | None = None):
    """Retorna lista de patches para usar em with aninhados."""
    return [
        patch("app.services.fastpath_v2_service.load_digest", return_value=digest),
        patch(
            "app.services.fastpath_v2_service.resolve_message_aliases",
            side_effect=lambda agent_id, msg: (msg, {}),
        ),
        patch(
            "app.services.fastpath_v2_service.db_execute.execute",
            return_value=_ok_result(exec_rows, exec_cols),
        ),
        patch("app.services.fastpath_v2_service.analytics_service.record_tables_mentioned"),
        patch("app.services.fastpath_v2_service.analytics_service.record_intent"),
        patch("app.services.fastpath_v2_service.analytics_service.record_aliases_used"),
    ]


# ─── Testes: fallback quando não há digest ───────────────────────────────────

@pytest.mark.anyio
async def test_no_digest_returns_none():
    agent = _make_agent()
    session = _make_session()
    with patch("app.services.fastpath_v2_service.load_digest", return_value=None):
        result = await fastpath_v2_service.execute(agent, "mostre clientes com status ativo", session)
    assert result is None


# ─── Testes: SELECT com filtro ────────────────────────────────────────────────

@pytest.mark.anyio
async def test_select_with_filter(digest_clientes):
    agent = _make_agent()
    session = _make_session()
    rows = [{"id": 1, "nome": "Ana", "status": "ativo", "cidade": "SP", "email": "ana@x.com"}]

    patches = _patch_all(digest_clientes, rows)
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        result = await fastpath_v2_service.execute(
            agent,
            "mostre clientes com status = ativo",
            session,
        )

    assert result is not None
    assert "V2" in result.intent
    assert "SELECT" in result.intent
    assert result.sql is not None
    assert "clientes" in result.table_name
    assert len(result.rows) == 1


@pytest.mark.anyio
async def test_select_with_limit(digest_clientes):
    agent = _make_agent()
    session = _make_session()
    rows = [{"id": i, "nome": f"X{i}", "status": "ativo", "cidade": "RJ", "email": ""} for i in range(5)]

    patches = _patch_all(digest_clientes, rows)
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        result = await fastpath_v2_service.execute(
            agent,
            "mostre os 5 primeiros clientes com status = ativo",
            session,
        )

    assert result is not None
    assert "LIMIT 5" in result.sql


# ─── Testes: COUNT ───────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_count_with_filter(digest_clientes):
    agent = _make_agent()
    session = _make_session()
    rows = [{"total": 42}]

    patches = _patch_all(digest_clientes, rows, ["total"])
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        result = await fastpath_v2_service.execute(
            agent,
            "quantos clientes com status = ativo",
            session,
        )

    assert result is not None
    assert "COUNT" in result.intent
    assert "42" in result.response


@pytest.mark.anyio
async def test_count_basic(digest_clientes):
    agent = _make_agent()
    session = _make_session()
    rows = [{"total": 100}]

    patches = _patch_all(digest_clientes, rows, ["total"])
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        result = await fastpath_v2_service.execute(
            agent,
            "quantos clientes existem",
            session,
        )

    assert result is not None
    assert "COUNT" in result.intent


# ─── Testes: JOIN ─────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_join_select(digest_com_join):
    agent = _make_agent()
    session = _make_session()
    rows = [{"id": 1, "nome": "Ana", "status": "ativo", "cliente_id": 1, "total": 150.0}]

    patches = _patch_all(digest_com_join, rows)
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        result = await fastpath_v2_service.execute(
            agent,
            "mostre pedidos e clientes com status = pago",
            session,
        )

    assert result is not None
    assert "JOIN" in result.intent
    assert "INNER JOIN" in result.sql


# ─── Testes: bloqueio de queries destrutivas ─────────────────────────────────

@pytest.mark.anyio
async def test_destructive_blocked(digest_clientes):
    agent = _make_agent()
    session = _make_session()

    with patch("app.services.fastpath_v2_service.load_digest", return_value=digest_clientes):
        for msg in [
            "delete clientes",
            "drop table clientes",
            "update clientes set status = inativo",
        ]:
            result = await fastpath_v2_service.execute(agent, msg, session)
            assert result is None, f"Deveria retornar None para: {msg!r}"


# ─── Testes: queries de schema passam para V1 ────────────────────────────────

@pytest.mark.anyio
async def test_schema_query_passes_to_v1(digest_clientes):
    agent = _make_agent()
    session = _make_session()

    with patch("app.services.fastpath_v2_service.load_digest", return_value=digest_clientes):
        for msg in [
            "descreva a tabela clientes",
            "show create table clientes",
            "quais tabelas existem",
            "listar triggers",
        ]:
            result = await fastpath_v2_service.execute(agent, msg, session)
            assert result is None, f"Deveria retornar None para: {msg!r}"


# ─── Testes: sem tabela identificada ─────────────────────────────────────────

@pytest.mark.anyio
async def test_no_table_identified_returns_none(digest_clientes):
    agent = _make_agent()
    session = _make_session()

    with patch("app.services.fastpath_v2_service.load_digest", return_value=digest_clientes):
        with patch(
            "app.services.fastpath_v2_service.resolve_message_aliases",
            side_effect=lambda a, m: (m, {}),
        ):
            result = await fastpath_v2_service.execute(
                agent,
                "qual é a capital do Brasil",
                session,
            )
    assert result is None


# ─── Testes: falha na execução SQL ───────────────────────────────────────────

@pytest.mark.anyio
async def test_sql_execution_failure_returns_none(digest_clientes):
    agent = _make_agent()
    session = _make_session()
    failed_result = DBExecuteResult(
        success=False,
        rows=[],
        rows_affected=0,
        columns=[],
        execution_time_ms=0.0,
        sql_executed="",
        error="Table 'test_db.clientes' doesn't exist",
        truncated=False,
    )

    with patch("app.services.fastpath_v2_service.load_digest", return_value=digest_clientes):
        with patch(
            "app.services.fastpath_v2_service.resolve_message_aliases",
            side_effect=lambda a, m: (m, {}),
        ):
            with patch(
                "app.services.fastpath_v2_service.db_execute.execute",
                return_value=failed_result,
            ):
                result = await fastpath_v2_service.execute(
                    agent,
                    "mostre clientes com status = ativo",
                    session,
                )
    assert result is None


# ─── Testes: analytics são chamados ──────────────────────────────────────────

@pytest.mark.anyio
async def test_analytics_recorded(digest_clientes):
    agent = _make_agent()
    session = _make_session()
    rows = [{"id": 1, "nome": "X", "status": "ativo", "cidade": "SP", "email": ""}]

    with patch("app.services.fastpath_v2_service.load_digest", return_value=digest_clientes):
        with patch(
            "app.services.fastpath_v2_service.resolve_message_aliases",
            side_effect=lambda a, m: (m, {}),
        ):
            with patch(
                "app.services.fastpath_v2_service.db_execute.execute",
                return_value=_ok_result(rows),
            ):
                with patch("app.services.fastpath_v2_service.analytics_service.record_tables_mentioned") as mock_tables:
                    with patch("app.services.fastpath_v2_service.analytics_service.record_intent") as mock_intent:
                        result = await fastpath_v2_service.execute(
                            agent,
                            "mostre clientes com status = ativo",
                            session,
                        )

    assert result is not None
    mock_tables.assert_called_once()
    mock_intent.assert_called_once()


# ─── Testes: resposta formatada ───────────────────────────────────────────────

@pytest.mark.anyio
async def test_response_format_select(digest_clientes):
    agent = _make_agent()
    session = _make_session()
    rows = [{"id": 1, "nome": "Ana", "status": "ativo", "cidade": "SP", "email": "ana@x.com"}]

    patches = _patch_all(digest_clientes, rows)
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        result = await fastpath_v2_service.execute(
            agent,
            "mostre clientes com status = ativo",
            session,
        )

    assert result is not None
    assert "[RESUMO]" in result.response
    assert "[SQL]" in result.response
    assert "[RESULTADO]" in result.response
    assert "[STATUS]" in result.response
    assert "```sql" in result.response


@pytest.mark.anyio
async def test_response_format_count(digest_clientes):
    agent = _make_agent()
    session = _make_session()
    rows = [{"total": 7}]

    patches = _patch_all(digest_clientes, rows, ["total"])
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        result = await fastpath_v2_service.execute(
            agent,
            "quantos clientes com status = ativo",
            session,
        )

    assert result is not None
    assert "7" in result.response
    assert "[RESUMO]" in result.response
