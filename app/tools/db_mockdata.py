"""
db_mockdata: Geração de mock data para tabelas MySQL.
Gera dados fictícios coerentes respeitando a estrutura real do banco.
"""
import random
import string
from datetime import datetime, timedelta
from typing import Optional

from app.core.logger import get_logger
from app.schemas.agent import AgentConfig
from app.schemas.execution import DBExecuteRequest, DBExecuteResult
from app.tools import db_execute as executor
from app.tools import db_introspection as introspect

logger = get_logger("db_mockdata")


def generate_and_insert(
    agent: AgentConfig,
    table_name: str,
    rows: int = 10,
    dry_run: bool = False,
) -> DBExecuteResult:
    """
    Gera e insere mock data em uma tabela.
    
    1. Consulta a estrutura real da tabela
    2. Gera valores plausíveis para cada coluna
    3. Cria INSERT SQL
    4. Executa (ou retorna SQL se dry_run)
    
    Args:
        agent: Agente especialista com acesso ao banco.
        table_name: Nome da tabela alvo.
        rows: Quantidade de linhas a gerar.
        dry_run: Se True, retorna SQL sem executar.
    """
    # 1. Introspectar a tabela
    desc_result = introspect.describe_table(agent, table_name)
    if not desc_result.success:
        return DBExecuteResult(
            success=False,
            error=f"Não foi possível inspecionar tabela '{table_name}': {desc_result.error}",
        )

    columns_info = desc_result.rows
    if not columns_info:
        return DBExecuteResult(
            success=False,
            error=f"Tabela '{table_name}' não retornou colunas ou não existe",
        )

    # 2. Filtrar colunas que podem receber valor (excluir AUTO_INCREMENT)
    insertable_cols = [
        col for col in columns_info
        if "auto_increment" not in (col.get("Extra") or "").lower()
    ]

    if not insertable_cols:
        return DBExecuteResult(
            success=False,
            error=f"Todas as colunas de '{table_name}' são AUTO_INCREMENT. Nada a inserir.",
        )

    col_names = [col["Field"] for col in insertable_cols]
    
    # 3. Gerar valores para cada linha
    value_rows = []
    for _ in range(min(rows, 100)):  # Limitar a 100 para segurança
        row_vals = [_generate_value(col) for col in insertable_cols]
        value_rows.append(row_vals)

    # 4. Construir INSERT SQL
    cols_escaped = ", ".join(f"`{c}`" for c in col_names)
    
    # Construir VALUES
    values_parts = []
    for row in value_rows:
        formatted = ", ".join(_format_value(v) for v in row)
        values_parts.append(f"({formatted})")
    
    sql = f"INSERT INTO `{table_name}` ({cols_escaped}) VALUES\n" + ",\n".join(values_parts)

    logger.info(f"Mock data gerado | tabela={table_name} | linhas={rows} | dry_run={dry_run}")

    if dry_run:
        return DBExecuteResult(
            success=True,
            sql_executed=sql,
            rows=[],
        )

    return executor.execute(
        DBExecuteRequest(sql=sql, mode="write"),
        agent,
    )


def _generate_value(col: dict) -> object:
    """
    Gera um valor plausível para uma coluna baseado no tipo e nome.
    """
    field_name = (col.get("Field") or "").lower()
    col_type = (col.get("Type") or "").lower()
    nullable = (col.get("Null") or "NO").upper() == "YES"
    has_default = col.get("Default") is not None

    # Se NULL e temos default, pode usar None às vezes
    if nullable and has_default and random.random() < 0.1:
        return None

    # Por tipo de dado
    if "int" in col_type:
        return _generate_int(field_name, col_type)
    elif "decimal" in col_type or "float" in col_type or "double" in col_type:
        return round(random.uniform(1.0, 9999.99), 2)
    elif "tinyint(1)" in col_type:  # Boolean
        return random.randint(0, 1)
    elif "tinyint" in col_type:
        return random.randint(0, 127)
    elif "datetime" in col_type or "timestamp" in col_type:
        return _generate_datetime()
    elif "date" in col_type:
        return _generate_date()
    elif "time" in col_type:
        return f"{random.randint(0, 23):02d}:{random.randint(0, 59):02d}:00"
    elif "year" in col_type:
        return random.randint(2020, 2025)
    elif "text" in col_type or "longtext" in col_type or "mediumtext" in col_type:
        return _generate_text(field_name, 50)
    elif "varchar" in col_type or "char" in col_type:
        max_len = _extract_length(col_type, 50)
        return _generate_string(field_name, min(max_len, 50))
    elif "enum" in col_type:
        options = _extract_enum_options(col_type)
        return random.choice(options) if options else "opcao1"
    elif "json" in col_type:
        return '{"mock": true}'
    else:
        return f"mock_{_random_suffix()}"


def _generate_int(field_name: str, col_type: str) -> int:
    """Gera inteiro plausível baseado no nome da coluna."""
    if any(kw in field_name for kw in ["id_", "_id", "fk_"]):
        return random.randint(1, 100)
    if "idade" in field_name or "age" in field_name:
        return random.randint(18, 80)
    if "qtd" in field_name or "quantity" in field_name or "quantidade" in field_name:
        return random.randint(1, 500)
    if "ano" in field_name or "year" in field_name:
        return random.randint(2020, 2025)
    return random.randint(1, 10000)


def _generate_string(field_name: str, max_len: int) -> str:
    """Gera string plausível baseada no nome da coluna."""
    nomes = ["Ana", "Carlos", "Maria", "Pedro", "Juliana", "Roberto", "Fernanda", "Lucas"]
    sobrenomes = ["Silva", "Santos", "Oliveira", "Costa", "Rodrigues", "Ferreira"]
    
    if any(kw in field_name for kw in ["nome", "name", "first"]):
        return random.choice(nomes)[:max_len]
    if any(kw in field_name for kw in ["sobrenome", "lastname", "surname"]):
        return random.choice(sobrenomes)[:max_len]
    if "email" in field_name:
        nome = random.choice(nomes).lower()
        dom = random.choice(["gmail.com", "outlook.com", "empresa.com.br"])
        return f"{nome}{random.randint(1,999)}@{dom}"[:max_len]
    if "telefone" in field_name or "phone" in field_name or "celular" in field_name:
        return f"({random.randint(11,99)}) {random.randint(9000,9999)}-{random.randint(1000,9999)}"[:max_len]
    if "cep" in field_name or "zip" in field_name:
        return f"{random.randint(10000, 99999)}-{random.randint(100, 999)}"[:max_len]
    if "cpf" in field_name:
        return f"{random.randint(100,999)}.{random.randint(100,999)}.{random.randint(100,999)}-{random.randint(10,99)}"[:max_len]
    if "descricao" in field_name or "description" in field_name or "obs" in field_name:
        return _generate_text(field_name, max_len)
    if any(kw in field_name for kw in ["cidade", "city"]):
        cidades = ["São Paulo", "Rio de Janeiro", "Curitiba", "Belo Horizonte", "Porto Alegre"]
        return random.choice(cidades)[:max_len]
    if "status" in field_name:
        return random.choice(["ativo", "inativo", "pendente"])[:max_len]
    
    # Default: string aleatória legível
    return f"mock_{_random_suffix()}"[:max_len]


def _generate_text(field_name: str, max_len: int) -> str:
    words = ["texto", "descricao", "informacao", "dados", "conteudo", "registro", "detalhes"]
    text = " ".join(random.choices(words, k=random.randint(3, 8)))
    return text[:max_len]


def _generate_datetime() -> str:
    base = datetime(2024, 1, 1)
    delta = timedelta(days=random.randint(0, 730), hours=random.randint(0, 23), minutes=random.randint(0, 59))
    return (base + delta).strftime("%Y-%m-%d %H:%M:%S")


def _generate_date() -> str:
    base = datetime(2024, 1, 1)
    delta = timedelta(days=random.randint(0, 730))
    return (base + delta).strftime("%Y-%m-%d")


def _extract_length(col_type: str, default: int = 50) -> int:
    """Extrai tamanho máximo de tipo como varchar(100)."""
    import re
    match = re.search(r"\((\d+)\)", col_type)
    return int(match.group(1)) if match else default


def _extract_enum_options(col_type: str) -> list[str]:
    """Extrai opções de um tipo ENUM."""
    import re
    matches = re.findall(r"'([^']+)'", col_type)
    return matches


def _format_value(val: object) -> str:
    """Formata um valor para SQL."""
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "1" if val else "0"
    if isinstance(val, (int, float)):
        return str(val)
    # String: escapar aspas simples
    escaped = str(val).replace("'", "''")
    return f"'{escaped}'"


def _random_suffix(length: int = 6) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))
