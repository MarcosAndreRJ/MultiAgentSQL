"""
Testes para o utilitário text_formatter.
"""
from app.utils.text_formatter import format_rows

def test_format_rows_basic():
    rows = [
        {"id": 1, "nome": "Projeto A", "status": "Ativo"},
        {"id": 2, "nome": "Projeto B", "status": "Pendente"}
    ]
    cols = ["id", "nome", "status"]
    
    result = format_rows(rows, cols)
    
    assert "id" in result
    assert "nome" in result
    assert "Projeto A" in result
    assert "Projeto B" in result
    assert "-+-" in result # Separador

def test_format_rows_empty():
    assert format_rows([]) == "(sem resultados)"

def test_format_rows_truncation():
    rows = [{"id": i} for i in range(10)]
    result = format_rows(rows, max_rows=5)
    
    assert "id" in result
    assert "(5 linhas omitidas)" in result
    # Deve ter o header + separador + 5 linhas = 7 linhas no total
    assert len(result.split("\n")) == 8 # 1 header + 1 sep + 5 rows + 1 omited note (if present on new line)
    # Na verdade, format_rows adiciona a nota como uma linha extra se exceder max_rows.

def test_format_rows_no_cols():
    rows = [{"a": 1, "b": 2}]
    result = format_rows(rows)
    assert "a" in result
    assert "b" in result
