"""
SQL Classifier: analisa e classifica SQL quanto ao tipo e nível de risco.
Responsabilidade: identificar o que o SQL faz, sem decisão de execução.
A decisão de executar ou bloquear é do guard_engine.
"""
import re
from typing import Optional

from app.schemas.guard import SQLClassification
from app.core.logger import get_logger

logger = get_logger("sql_classifier")

# Mapeamento de palavras-chave para tipos SQL
SQL_TYPE_PATTERNS: list[tuple[str, str]] = [
    (r"^\s*SELECT\b", "SELECT"),
    (r"^\s*SHOW\b", "SHOW"),
    (r"^\s*DESCRIBE\b|^\s*DESC\b", "DESCRIBE"),
    (r"^\s*EXPLAIN\b", "EXPLAIN"),
    (r"^\s*INSERT\b", "INSERT"),
    (r"^\s*UPDATE\b", "UPDATE"),
    (r"^\s*DELETE\b", "DELETE"),
    (r"^\s*DROP\b", "DROP"),
    (r"^\s*TRUNCATE\b", "TRUNCATE"),
    (r"^\s*CREATE\b", "CREATE"),
    (r"^\s*ALTER\b", "ALTER"),
    (r"^\s*CALL\b", "CALL"),
    (r"^\s*DELIMITER\b", "DELIMITER"),
    (r"^\s*START\s+TRANSACTION\b|^\s*BEGIN\b", "TRANSACTION"),
    (r"^\s*COMMIT\b", "COMMIT"),
    (r"^\s*ROLLBACK\b", "ROLLBACK"),
]

# Tipos considerados de leitura (LOW risk por padrão)
READ_TYPES = {"SELECT", "SHOW", "DESCRIBE", "EXPLAIN"}

# Tipos de escrita (MEDIUM risk por padrão)
WRITE_TYPES = {"INSERT", "UPDATE", "CALL"}

# Tipos destrutivos (HIGH risk)
DESTRUCTIVE_TYPES = {"DELETE", "DROP", "TRUNCATE"}

# Tipos de estrutura (avalia subtipos para risco)
DDL_TYPES = {"CREATE", "ALTER"}


def classify_sql(sql: str) -> SQLClassification:
    """
    Classifica um SQL quanto ao tipo e nível de risco.
    
    Args:
        sql: O SQL a ser classificado (pode ser multi-statement).
        
    Returns:
        SQLClassification com tipo, risco e metadados.
    """
    if not sql or not sql.strip():
        return SQLClassification(
            sql_type="EMPTY",
            risk_level="low",
            warnings=["SQL vazio recebido"],
        )

    sql_clean = sql.strip()

    # Detectar multi-statement (múltiplas sentenças)
    is_multi = _is_multi_statement(sql_clean)

    # Identificar o tipo principal (primeiro statement)
    sql_type = _detect_sql_type(sql_clean)

    # Verificar presença de WHERE em UPDATE/DELETE
    has_where = _has_where_clause(sql_clean, sql_type)

    # Objetos afetados
    affected_objects = _extract_affected_objects(sql_clean, sql_type)

    # Avaliar se é destrutivo
    is_destructive = _is_destructive(sql_clean, sql_type)

    # Calcular nível de risco
    risk_level, warnings = _calculate_risk(
        sql_type=sql_type,
        has_where=has_where,
        is_multi=is_multi,
        is_destructive=is_destructive,
        sql=sql_clean,
    )

    classification = SQLClassification(
        sql_type=sql_type,
        risk_level=risk_level,
        has_where=has_where,
        is_multi_statement=is_multi,
        is_destructive=is_destructive,
        warnings=warnings,
        affected_objects=affected_objects,
    )

    logger.debug(f"SQL classificado: type={sql_type}, risk={risk_level}, multi={is_multi}")
    return classification


def _detect_sql_type(sql: str) -> str:
    """Identifica o tipo principal do SQL."""
    sql_upper = sql.upper().strip()
    for pattern, sql_type in SQL_TYPE_PATTERNS:
        if re.match(pattern, sql_upper, re.IGNORECASE):
            return sql_type
    return "OTHER"


def _has_where_clause(sql: str, sql_type: str) -> bool:
    """Verifica se UPDATE ou DELETE têm cláusula WHERE."""
    if sql_type not in ("UPDATE", "DELETE"):
        return True  # Não se aplica, considerar como OK

    # Busca WHERE fora de subqueries (simplificado)
    # Remover strings literais para não confundir
    sql_clean = re.sub(r"'[^']*'|\"[^\"]*\"", "''", sql)
    has = bool(re.search(r"\bWHERE\b", sql_clean, re.IGNORECASE))
    return has


def _is_multi_statement(sql: str) -> bool:
    """Detecta se o SQL contém múltiplas declarações."""
    # Remover strings literais
    sql_clean = re.sub(r"'[^']*'|\"[^\"]*\"", "''", sql)
    # Contar pontos e vírgula (exceto dentro de DELIMITER blocks)
    statements = [s.strip() for s in sql_clean.split(";") if s.strip()]
    return len(statements) > 1


def _is_destructive(sql: str, sql_type: str) -> bool:
    """Determina se a operação é potencialmente destrutiva."""
    if sql_type in DESTRUCTIVE_TYPES:
        return True
    if sql_type == "ALTER":
        # ALTER com DROP COLUMN é destrutivo
        if re.search(r"\bDROP\s+COLUMN\b", sql, re.IGNORECASE):
            return True
        if re.search(r"\bDROP\s+INDEX\b", sql, re.IGNORECASE):
            return True
    return False


def _extract_affected_objects(sql: str, sql_type: str) -> list[str]:
    """Extrai nomes de objetos afetados pelo SQL."""
    objects = []
    try:
        if sql_type in ("SELECT", "DELETE", "UPDATE", "TRUNCATE"):
            # FROM / UPDATE nome_tabela
            match = re.search(r"\b(?:FROM|UPDATE|TRUNCATE(?:\s+TABLE)?)\s+`?([a-zA-Z0-9_]+)`?", sql, re.IGNORECASE)
            if match:
                objects.append(match.group(1))
        elif sql_type in ("DROP", "CREATE", "ALTER"):
            # DROP TABLE nome / CREATE TABLE nome / ALTER TABLE nome
            match = re.search(r"\b(?:TABLE|VIEW|TRIGGER|PROCEDURE|FUNCTION|INDEX)\s+(?:IF\s+(?:NOT\s+)?EXISTS\s+)?`?([a-zA-Z0-9_]+)`?", sql, re.IGNORECASE)
            if match:
                objects.append(match.group(1))
        elif sql_type == "INSERT":
            match = re.search(r"\bINTO\s+`?([a-zA-Z0-9_]+)`?", sql, re.IGNORECASE)
            if match:
                objects.append(match.group(1))
    except Exception:
        pass
    return objects


def _calculate_risk(
    sql_type: str,
    has_where: bool,
    is_multi: bool,
    is_destructive: bool,
    sql: str,
) -> tuple[str, list[str]]:
    """Calcula nível de risco e retorna avisos."""
    warnings = []
    risk_level = "low"

    if sql_type in READ_TYPES:
        risk_level = "low"

    elif sql_type == "INSERT":
        risk_level = "medium"

    elif sql_type == "UPDATE":
        if has_where:
            risk_level = "medium"
        else:
            risk_level = "high"
            warnings.append("UPDATE sem cláusula WHERE — afeta todas as linhas")

    elif sql_type == "DELETE":
        risk_level = "high"
        if not has_where:
            warnings.append("DELETE sem cláusula WHERE — remove todos os registros")

    elif sql_type in ("DROP", "TRUNCATE"):
        risk_level = "high"
        warnings.append(f"{sql_type} é uma operação destrutiva e irreversível")

    elif sql_type == "ALTER":
        if is_destructive:
            risk_level = "high"
            warnings.append("ALTER contém DROP COLUMN ou operação destrutiva")
        else:
            risk_level = "medium"

    elif sql_type == "CREATE":
        risk_level = "low"

    elif sql_type in ("CALL",):
        risk_level = "medium"
        warnings.append("CALL executa procedure — verifique efeitos colaterais")

    elif sql_type in ("TRANSACTION", "COMMIT", "ROLLBACK"):
        risk_level = "medium"

    elif sql_type == "DELIMITER":
        risk_level = "medium"

    else:
        risk_level = "medium"

    # Multi-statement sempre eleva para ao menos medium
    if is_multi and risk_level == "low":
        risk_level = "medium"
        warnings.append("SQL multi-statement detectado")

    return risk_level, warnings
