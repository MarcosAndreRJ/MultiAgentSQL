import pytest
from app.services.fast_path_router import detect_fast_path_intent, FastPathIntentType

def test_count_table_queries():
    queries = [
        ("quantos registros tem na tabela usuarios", "usuarios"),
        ("count de items", "items"),
        ("quantos itens existem em orders?", "orders"),
        ("me diga quantos registros existem em transacao", "transacao"),
        ("count da tabela clientes", "clientes"),
        ("quantos registros tem na tabela tbl_foo", "tbl_foo")
    ]
    for q, table in queries:
        res = detect_fast_path_intent(q)
        assert res.matched is True
        assert res.intent == FastPathIntentType.COUNT_TABLE
        assert res.table_name == table

def test_list_tables_queries():
    queries = [
        "liste as tabelas",
        "mostrar tabelas",
        "quais tabelas existem?",
        "quais as tabelas existem",
        "list tables",
        "listar tabelas"
    ]
    for q in queries:
        res = detect_fast_path_intent(q)
        assert res.matched is True
        assert res.intent == FastPathIntentType.LIST_TABLES

def test_describe_table_queries():
    queries = [
        ("descreva a tabela Projeto", "projeto"),
        ("estrutura da tabela users", "users"),
        ("show columns from Projeto", "projeto"),
        ("me mostra as colunas da tabela Empresa", "empresa"),
        ("describe usuarios", "usuarios")
    ]
    for q, table in queries:
        res = detect_fast_path_intent(q)
        assert res.matched is True, f"Failed on {q}"
        assert res.intent == FastPathIntentType.DESCRIBE_TABLE
        assert res.table_name == table

def test_show_create_table_queries():
    queries = [
        ("me mostra o ddl da tabela Projeto", "projeto"),
        ("show create table Projeto", "projeto"),
        ("criação da tabela users", "users"),
        ("ddl da tabela clientes", "clientes"),
        ("script da tabela orders", "orders")
    ]
    for q, table in queries:
        res = detect_fast_path_intent(q)
        assert res.matched is True, f"Failed on {q}"
        assert res.intent == FastPathIntentType.SHOW_CREATE_TABLE
        assert res.table_name == table

def test_list_views_triggers():
    assert detect_fast_path_intent("liste as views").intent == FastPathIntentType.LIST_VIEWS
    assert detect_fast_path_intent("quais views existem").intent == FastPathIntentType.LIST_VIEWS
    assert detect_fast_path_intent("listar triggers").intent == FastPathIntentType.LIST_TRIGGERS
    assert detect_fast_path_intent("quais as procedures existem?").intent == FastPathIntentType.LIST_TRIGGERS

def test_destructive_commands_prevent_fast_path():
    queries = [
        "delete from usuarios",
        "quantos registros tem depois do drop table users?",
        "count da tabela clientes e update",
        "liste as tabelas e truncate foo"
    ]
    for q in queries:
        res = detect_fast_path_intent(q)
        assert res.matched is False
        assert res.intent == FastPathIntentType.NONE

def test_fallback_cases():
    queries = [
        "qual o cliente com mais compras?",
        "faça um join entre A e B",
        "me explique o que é um index",
        "oi, tudo bem?"
    ]
    for q in queries:
        res = detect_fast_path_intent(q)
        assert res.matched is False
        assert res.intent == FastPathIntentType.NONE

def test_table_name_extraction_with_backticks():
    res = detect_fast_path_intent("quantos registros tem na tabela ```users```")
    assert res.matched is True
    assert res.intent == FastPathIntentType.COUNT_TABLE
    assert res.table_name == "users"

    res = detect_fast_path_intent("descreva a tabela `orders`")
    # Our regex looks for generic words, currently backticks aren't in regex 
    # but we handle markdown block ticks. Let's make sure code handles simple backticks if requested.
    # User requested robust extraction: `tbl Projeto` or `table users`.
