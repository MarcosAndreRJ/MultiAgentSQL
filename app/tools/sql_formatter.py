"""
sql_formatter: Formatação e normalização de SQL para exibição.
Não altera semântica — apenas limpa e formata para leitura humana.
"""
import re


def format_sql(sql: str) -> str:
    """
    Formata SQL para exibição legível.
    Não altera a semântica do SQL.
    
    Args:
        sql: SQL bruto.
        
    Returns:
        SQL formatado.
    """
    if not sql or not sql.strip():
        return sql

    result = sql.strip()
    
    # Normalizar espaços múltiplos (exceto em strings)
    result = _normalize_whitespace(result)
    
    return result


def _normalize_whitespace(sql: str) -> str:
    """Remove espaços múltiplos fora de strings literais."""
    # Substituição simples de múltiplos espaços que não esteja em string
    # Para um formatter real completo, seria necessário um parser SQL
    # Esta implementação é conservadora para não alterar o SQL
    parts = re.split(r"('[^']*'|\"[^\"]*\")", sql)
    normalized_parts = []
    for i, part in enumerate(parts):
        if i % 2 == 0:  # Parte fora de strings
            # Normalizar apenas espaços em excesso
            part = re.sub(r"[ \t]+", " ", part)
        normalized_parts.append(part)
    return "".join(normalized_parts)


def truncate_for_display(sql: str, max_len: int = 500) -> str:
    """Trunca SQL longo para exibição."""
    if len(sql) <= max_len:
        return sql
    return sql[:max_len] + f"\n... [truncado - {len(sql)} chars total]"


def extract_sql_from_text(text: str) -> list[str]:
    """
    Extrai blocos SQL de um texto (por exemplo, resposta do LLM).
    Busca por blocos ```sql ... ``` ou ``` ... ```.
    
    Returns:
        Lista de SQLs encontrados.
    """
    sqls = []
    
    # Padrão: ```sql ... ``` ou ```SQL ... ```
    pattern = r"```(?:sql|SQL|mysql|MySQL)?\s*\n?(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    
    for match in matches:
        sql = match.strip()
        if sql:
            sqls.append(sql)
    
    return sqls
