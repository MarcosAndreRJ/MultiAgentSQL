"""
Testes unitários para app/services/filter_parser.py
"""
import pytest
from app.services.filter_parser import (
    parse_slots,
    parse_limit_from_text,
    parse_order_from_text,
    QueryFilter,
    OrderByClause,
    ParsedSlots,
)


# ─── parse_slots: filtros com operadores simbólicos ───────────────────────────

class TestExplicitOperatorFilters:
    def test_equal_symbol(self):
        s = parse_slots("status = ativo")
        assert len(s.filters) == 1
        f = s.filters[0]
        assert f.field == "status"
        assert f.op == "="
        assert f.value == "ativo"

    def test_equal_number(self):
        s = parse_slots("id = 42")
        assert s.filters[0].value == 42

    def test_greater_than(self):
        s = parse_slots("id > 10")
        f = s.filters[0]
        assert f.op == ">"
        assert f.value == 10

    def test_less_than(self):
        s = parse_slots("preco < 99.99")
        f = s.filters[0]
        assert f.op == "<"
        assert abs(f.value - 99.99) < 0.001

    def test_gte(self):
        s = parse_slots("quantidade >= 5")
        assert s.filters[0].op == ">="

    def test_lte(self):
        s = parse_slots("estoque <= 100")
        assert s.filters[0].op == "<="

    def test_not_equal(self):
        s = parse_slots("status != inativo")
        assert s.filters[0].op == "!="

    def test_diamond_not_equal(self):
        s = parse_slots("tipo <> cancelado")
        assert s.filters[0].op == "!="

    def test_quoted_value(self):
        s = parse_slots('cidade = "São Paulo"')
        assert s.filters[0].value == "São Paulo"

    def test_single_quoted_value(self):
        s = parse_slots("nome = 'João'")
        assert s.filters[0].value == "João"

    def test_float_value(self):
        s = parse_slots("taxa = 3.14")
        assert abs(s.filters[0].value - 3.14) < 0.001


# ─── parse_slots: filtros com operadores textuais ────────────────────────────

class TestTextualOperatorFilters:
    def test_contem(self):
        s = parse_slots("nome contém joao")
        assert len(s.filters) == 1
        f = s.filters[0]
        assert f.op == "LIKE"
        assert f.value == "%joao%"

    def test_like(self):
        s = parse_slots("descricao like abc")
        f = s.filters[0]
        assert f.op == "LIKE"
        assert f.value == "%abc%"

    def test_e_igual(self):
        s = parse_slots("status é ativo")
        assert s.filters[0].op == "="
        assert s.filters[0].value == "ativo"

    def test_nao_e(self):
        s = parse_slots("status não é inativo")
        assert s.filters[0].op == "!="
        assert s.filters[0].value == "inativo"

    def test_maior_que(self):
        s = parse_slots("idade maior que 18")
        assert s.filters[0].op == ">"
        assert s.filters[0].value == 18

    def test_menor_que(self):
        s = parse_slots("preco menor que 50")
        assert s.filters[0].op == "<"
        assert s.filters[0].value == 50

    def test_is_null(self):
        s = parse_slots("email nulo")
        assert s.filters[0].op == "IS NULL"
        assert s.filters[0].value is None

    def test_is_not_null(self):
        s = parse_slots("email não nulo")
        assert s.filters[0].op == "IS NOT NULL"

    def test_igual_a(self):
        s = parse_slots("tipo igual a premium")
        assert s.filters[0].op == "="
        assert s.filters[0].value == "premium"


# ─── parse_slots: limite ─────────────────────────────────────────────────────

class TestLimitExtraction:
    def test_primeiros(self):
        s = parse_slots("mostre os 10 primeiros")
        assert s.limit == 10

    def test_limite(self):
        s = parse_slots("limite 20")
        assert s.limit == 20

    def test_top(self):
        s = parse_slots("top 5 resultados")
        assert s.limit == 5

    def test_maximo(self):
        s = parse_slots("máximo 100 linhas")
        assert s.limit == 100

    def test_sem_limit(self):
        s = parse_slots("mostre todos os clientes")
        assert s.limit is None

    def test_parse_limit_standalone(self):
        assert parse_limit_from_text("top 25 registros") == 25
        assert parse_limit_from_text("sem limit") is None


# ─── parse_slots: ordenação ──────────────────────────────────────────────────

class TestOrderByExtraction:
    def test_orderby_asc(self):
        s = parse_slots("ordenado por nome")
        assert len(s.order_by) == 1
        assert s.order_by[0].field == "nome"
        assert s.order_by[0].direction == "asc"

    def test_orderby_desc(self):
        s = parse_slots("ordenado por id desc")
        assert s.order_by[0].direction == "desc"

    def test_orderby_descendente(self):
        s = parse_slots("ordenado por criado_em descendente")
        assert s.order_by[0].direction == "desc"

    def test_order_by_english(self):
        s = parse_slots("order by name asc")
        assert s.order_by[0].field == "name"
        assert s.order_by[0].direction == "asc"

    def test_por_campo_desc(self):
        s = parse_slots("resultados por data desc")
        assert s.order_by[0].field == "data"
        assert s.order_by[0].direction == "desc"

    def test_parse_order_standalone(self):
        clauses = parse_order_from_text("order by nome desc")
        assert len(clauses) == 1
        assert clauses[0].direction == "desc"


# ─── parse_slots: combinado ───────────────────────────────────────────────────

class TestCombinedSlots:
    def test_filter_and_limit(self):
        s = parse_slots("status = ativo limite 10")
        assert len(s.filters) == 1
        assert s.filters[0].value == "ativo"
        assert s.limit == 10

    def test_filter_and_order(self):
        s = parse_slots("status = ativo ordenado por nome")
        assert len(s.filters) == 1
        assert len(s.order_by) == 1
        assert s.order_by[0].field == "nome"

    def test_full_combo(self):
        s = parse_slots("tipo = premium ordenado por nome desc limite 5")
        assert len(s.filters) == 1
        assert s.filters[0].field == "tipo"
        assert s.filters[0].value == "premium"
        assert s.order_by[0].direction == "desc"
        assert s.limit == 5

    def test_empty_message(self):
        s = parse_slots("")
        assert s.filters == []
        assert s.order_by == []
        assert s.limit is None

    def test_no_slots(self):
        s = parse_slots("mostre os clientes")
        # Pode ou não ter filtros, mas não deve falhar
        assert isinstance(s, ParsedSlots)

    def test_to_dict(self):
        s = parse_slots("id = 1 limite 5")
        d = s.to_dict()
        assert "filters" in d
        assert "limit" in d
        assert d["limit"] == 5
