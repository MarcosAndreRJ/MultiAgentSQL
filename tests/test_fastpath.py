"""
Testes para fastpath_service: detect_intent e execute_fast_path.

Cobre:
  - Detecção de LIST_RECORDS (intent novo)
  - Detecção dos intents existentes via detect_intent
  - Segurança: comandos destrutivos devem retornar None
  - execute_fast_path com mocks de db_execute / db_introspection
  - Fallback para LLM quando tabela não existe ou query falha
"""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from app.services.fastpath_service import (
    LIST_RECORDS_INTENT,
    FastPathResult,
    detect_intent,
    execute_fast_path,
)
from app.services.fast_path_router import FastPathIntentType


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _mock_agent(agent_id: str = "test-agent") -> MagicMock:
    agent = MagicMock()
    agent.id = agent_id
    agent.database = MagicMock()
    return agent


def _mock_session(session_id: str = "s1") -> MagicMock:
    from app.schemas.chat import Session
    return Session(session_id=session_id, agent_id="test-agent")


def _introspect_ok(rows=None, columns=None) -> MagicMock:
    r = MagicMock()
    r.success = True
    r.rows = rows or [{"Field": "id", "Type": "int"}]
    r.columns = columns or ["Field", "Type"]
    return r


def _introspect_fail() -> MagicMock:
    r = MagicMock()
    r.success = False
    r.rows = []
    r.columns = []
    return r


def _execute_ok(rows=None, columns=None) -> MagicMock:
    r = MagicMock()
    r.success = True
    r.rows = rows or [{"id": 1, "nome": "Teste"}]
    r.columns = columns or ["id", "nome"]
    r.error = None
    return r


def _execute_fail(error: str = "DB error") -> MagicMock:
    r = MagicMock()
    r.success = False
    r.rows = []
    r.error = error
    return r


# ─── detect_intent: LIST_RECORDS ──────────────────────────────────────────────

class TestDetectIntentListRecords:
    def test_listar_tabela(self):
        intent, table = detect_intent("listar Dica")
        assert intent == LIST_RECORDS_INTENT
        assert table == "Dica"

    def test_mostrar_registros_tabela(self):
        intent, table = detect_intent("mostrar registros Projeto")
        assert intent == LIST_RECORDS_INTENT
        assert table == "Projeto"

    def test_ver_tabela(self):
        intent, table = detect_intent("ver ClientePF")
        assert intent == LIST_RECORDS_INTENT
        assert table == "ClientePF"

    def test_exibir_tabela(self):
        intent, table = detect_intent("exibir Pedido")
        assert intent == LIST_RECORDS_INTENT
        assert table == "Pedido"

    def test_select_star_from(self):
        intent, table = detect_intent("select * from usuarios")
        assert intent == LIST_RECORDS_INTENT
        assert table == "usuarios"

    def test_select_star_sem_from(self):
        intent, table = detect_intent("select * clientes")
        assert intent == LIST_RECORDS_INTENT
        assert table == "clientes"

    def test_list_en(self):
        intent, table = detect_intent("list orders")
        assert intent == LIST_RECORDS_INTENT
        assert table == "orders"

    def test_nao_confundir_com_list_tables(self):
        intent, table = detect_intent("listar tabelas")
        # Deve ser LIST_TABLES, não LIST_RECORDS
        assert intent == FastPathIntentType.LIST_TABLES.value

    def test_ignore_word_banco(self):
        # "listar banco" não deve ser LIST_RECORDS
        intent, table = detect_intent("listar banco")
        assert intent != LIST_RECORDS_INTENT or table not in ("banco",)

    def test_ignore_word_dados(self):
        intent, table = detect_intent("listar dados")
        # "dados" está em _IGNORE_WORDS
        assert intent is None or table not in ("dados",)


# ─── detect_intent: intents existentes ───────────────────────────────────────

class TestDetectIntentExisting:
    def test_count_table(self):
        intent, table = detect_intent("quantos registros tem na tabela usuarios")
        assert intent == FastPathIntentType.COUNT_TABLE.value
        assert table == "usuarios"

    def test_count_em_notacao_curta(self):
        intent, table = detect_intent("count de clientes")
        assert intent == FastPathIntentType.COUNT_TABLE.value
        assert table == "clientes"

    def test_describe_table(self):
        intent, table = detect_intent("descreva a tabela Projeto")
        assert intent == FastPathIntentType.DESCRIBE_TABLE.value
        assert table.lower() == "projeto"

    def test_show_create_table(self):
        intent, table = detect_intent("ddl da tabela orders")
        assert intent == FastPathIntentType.SHOW_CREATE_TABLE.value
        assert table.lower() == "orders"

    def test_list_tables(self):
        intent, table = detect_intent("liste as tabelas")
        assert intent == FastPathIntentType.LIST_TABLES.value
        assert table is None

    def test_list_views(self):
        intent, table = detect_intent("listar as views")
        assert intent == FastPathIntentType.LIST_VIEWS.value

    def test_list_triggers(self):
        intent, table = detect_intent("listar triggers")
        assert intent == FastPathIntentType.LIST_TRIGGERS.value

    def test_no_match_complexo(self):
        intent, table = detect_intent("qual o cliente com mais compras?")
        assert intent is None

    def test_no_match_saudacao(self):
        intent, table = detect_intent("oi, tudo bem?")
        assert intent is None


# ─── detect_intent: segurança ─────────────────────────────────────────────────

class TestDetectIntentSecurity:
    def test_delete_bloqueado(self):
        intent, _ = detect_intent("delete from usuarios")
        assert intent is None

    def test_drop_bloqueado(self):
        intent, _ = detect_intent("quantos registros depois de drop table users")
        assert intent is None

    def test_update_bloqueado(self):
        intent, _ = detect_intent("listar Dica e update clientes")
        assert intent is None

    def test_truncate_bloqueado(self):
        intent, _ = detect_intent("truncate orders")
        assert intent is None

    def test_show_create_table_permitido(self):
        # "create" isolado com contexto "show create" é seguro
        intent, table = detect_intent("show create table orders")
        assert intent == FastPathIntentType.SHOW_CREATE_TABLE.value
        assert table.lower() == "orders"

    def test_ddl_da_tabela_permitido(self):
        intent, table = detect_intent("ddl da tabela clientes")
        assert intent == FastPathIntentType.SHOW_CREATE_TABLE.value
        assert table.lower() == "clientes"


# ─── execute_fast_path: LIST_RECORDS ──────────────────────────────────────────

class TestExecuteFastPathListRecords:
    def test_sucesso(self):
        agent = _mock_agent()
        session = _mock_session()

        with (
            patch("app.services.fastpath_service.db_introspection.introspect",
                  return_value=_introspect_ok()),
            patch("app.services.fastpath_service.db_execute.execute",
                  return_value=_execute_ok()),
            patch("app.services.fastpath_service.session_store"),
        ):
            result = asyncio.run(execute_fast_path(agent, "listar Dica", session))

        assert result is not None
        assert isinstance(result, FastPathResult)
        assert result.intent == LIST_RECORDS_INTENT
        assert result.table_name == "Dica"
        assert "SELECT * FROM `Dica` LIMIT 50" in result.sql
        assert "[RESULTADO]" in result.response

    def test_tabela_inexistente_retorna_none(self):
        agent = _mock_agent()
        session = _mock_session()

        with (
            patch("app.services.fastpath_service.db_introspection.introspect",
                  return_value=_introspect_fail()),
            patch("app.services.fastpath_service.session_store"),
        ):
            result = asyncio.run(execute_fast_path(agent, "listar TabelaInvalida", session))

        assert result is None

    def test_falha_no_execute_retorna_none(self):
        agent = _mock_agent()
        session = _mock_session()

        with (
            patch("app.services.fastpath_service.db_introspection.introspect",
                  return_value=_introspect_ok()),
            patch("app.services.fastpath_service.db_execute.execute",
                  return_value=_execute_fail()),
            patch("app.services.fastpath_service.session_store"),
        ):
            result = asyncio.run(execute_fast_path(agent, "listar Pedido", session))

        assert result is None

    def test_rows_na_resposta(self):
        agent = _mock_agent()
        session = _mock_session()
        rows = [{"id": 1, "nome": "A"}, {"id": 2, "nome": "B"}]

        with (
            patch("app.services.fastpath_service.db_introspection.introspect",
                  return_value=_introspect_ok()),
            patch("app.services.fastpath_service.db_execute.execute",
                  return_value=_execute_ok(rows=rows, columns=["id", "nome"])),
            patch("app.services.fastpath_service.session_store"),
        ):
            result = asyncio.run(execute_fast_path(agent, "listar Clientes", session))

        assert result is not None
        assert len(result.rows) == 2


# ─── execute_fast_path: COUNT ─────────────────────────────────────────────────

class TestExecuteFastPathCount:
    def test_count_sucesso(self):
        agent = _mock_agent()
        session = _mock_session()

        def introspect_side(ag, action, table=None):
            if action == "describe_table":
                return _introspect_ok()
            return _introspect_fail()

        with (
            patch("app.services.fastpath_service.db_introspection.introspect",
                  side_effect=introspect_side),
            patch("app.services.fastpath_service.db_execute.execute",
                  return_value=_execute_ok(rows=[{"total": 99}], columns=["total"])),
            patch("app.services.fastpath_service.session_store"),
        ):
            result = asyncio.run(
                execute_fast_path(agent, "quantos registros tem na tabela clientes", session)
            )

        assert result is not None
        assert result.intent == FastPathIntentType.COUNT_TABLE.value
        assert "COUNT(*)" in result.sql
        assert "99" in result.response

    def test_tabela_inexistente_retorna_none(self):
        agent = _mock_agent()
        session = _mock_session()

        with (
            patch("app.services.fastpath_service.db_introspection.introspect",
                  return_value=_introspect_fail()),
            patch("app.services.fastpath_service.session_store"),
        ):
            result = asyncio.run(
                execute_fast_path(agent, "quantos registros tem na tabela inexistente", session)
            )

        assert result is None


# ─── execute_fast_path: DESCRIBE ──────────────────────────────────────────────

class TestExecuteFastPathDescribe:
    def test_describe_sucesso(self):
        agent = _mock_agent()
        session = _mock_session()
        cols = ["Field", "Type", "Null", "Key"]
        rows = [{"Field": "id", "Type": "int(11)", "Null": "NO", "Key": "PRI"}]

        with (
            patch("app.services.fastpath_service.db_introspection.introspect",
                  return_value=_introspect_ok(rows=rows, columns=cols)),
            patch("app.services.fastpath_service.session_store"),
        ):
            result = asyncio.run(
                execute_fast_path(agent, "descreva a tabela Projeto", session)
            )

        assert result is not None
        assert result.intent == FastPathIntentType.DESCRIBE_TABLE.value
        assert result.table_name.lower() == "projeto"
        assert "DESCRIBE" in result.sql
        assert "id" in result.response


# ─── execute_fast_path: LIST_TABLES / VIEWS ───────────────────────────────────

class TestExecuteFastPathListTables:
    def test_list_tables_sucesso(self):
        agent = _mock_agent()
        session = _mock_session()
        rows = [{"Tables_in_db": "clientes"}, {"Tables_in_db": "pedidos"}]

        with (
            patch("app.services.fastpath_service.db_introspection.introspect",
                  return_value=_introspect_ok(rows=rows, columns=["Tables_in_db"])),
            patch("app.services.fastpath_service.session_store"),
        ):
            result = asyncio.run(
                execute_fast_path(agent, "liste as tabelas", session)
            )

        assert result is not None
        assert result.intent == FastPathIntentType.LIST_TABLES.value
        assert "clientes" in result.response

    def test_list_views_sucesso(self):
        agent = _mock_agent()
        session = _mock_session()
        rows = [{"VIEW_NAME": "vw_resumo"}]

        with (
            patch("app.services.fastpath_service.db_introspection.introspect",
                  return_value=_introspect_ok(rows=rows, columns=["VIEW_NAME"])),
            patch("app.services.fastpath_service.session_store"),
        ):
            result = asyncio.run(
                execute_fast_path(agent, "listar as views", session)
            )

        assert result is not None
        assert result.intent == FastPathIntentType.LIST_VIEWS.value


# ─── execute_fast_path: segurança ─────────────────────────────────────────────

class TestExecuteFastPathSecurity:
    def test_delete_nao_executa(self):
        agent = _mock_agent()
        session = _mock_session()

        with patch("app.services.fastpath_service.session_store"):
            result = asyncio.run(execute_fast_path(agent, "delete from usuarios", session))

        assert result is None

    def test_drop_nao_executa(self):
        agent = _mock_agent()
        session = _mock_session()

        with patch("app.services.fastpath_service.session_store"):
            result = asyncio.run(execute_fast_path(agent, "drop table clientes", session))

        assert result is None

    def test_update_nao_executa(self):
        agent = _mock_agent()
        session = _mock_session()

        with patch("app.services.fastpath_service.session_store"):
            result = asyncio.run(
                execute_fast_path(agent, "update pedidos set status='ok'", session)
            )

        assert result is None

    def test_mensagem_complexa_retorna_none(self):
        agent = _mock_agent()
        session = _mock_session()

        with patch("app.services.fastpath_service.session_store"):
            result = asyncio.run(
                execute_fast_path(agent, "faça um join entre clientes e pedidos", session)
            )

        assert result is None


# ─── Testes de _format_rows ───────────────────────────────────────────────────

class TestFormatRows:
    def test_vazio(self):
        from app.services.fastpath_service import _format_rows
        assert _format_rows([]) == "(sem resultados)"

    def test_uma_linha(self):
        from app.services.fastpath_service import _format_rows
        rows = [{"id": 1, "nome": "Teste"}]
        output = _format_rows(rows, ["id", "nome"])
        assert "1" in output
        assert "Teste" in output

    def test_limite_max_rows(self):
        from app.services.fastpath_service import _format_rows
        rows = [{"id": i} for i in range(100)]
        output = _format_rows(rows, ["id"], max_rows=10)
        assert "omitida" in output

    def test_colunas_inferidas_das_rows(self):
        from app.services.fastpath_service import _format_rows
        rows = [{"a": 1, "b": 2}]
        output = _format_rows(rows)
        assert "a" in output
        assert "b" in output
