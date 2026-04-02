"""
Utilitários de formatação de texto para o chat.
"""
from typing import List, Optional, Dict

def format_rows(rows: List[Dict], columns: Optional[List[str]] = None, max_rows: Optional[int] = None) -> str:
    """
    Formata lista de linhas (dicts) como uma tabela ASCII compatível com o frontend.
    
    O frontend espera o formato:
    Header 1 | Header 2
    ---------+---------
    Val 1    | Val 2
    """
    if not rows:
        return "(sem resultados)"

    display_rows = rows[:max_rows] if (max_rows is not None and max_rows > 0) else rows
    cols = columns or (list(display_rows[0].keys()) if display_rows else [])

    if not cols:
        return str(display_rows)

    # Calcular larguras de colunas (mínimo len do nome da coluna, máximo 50)
    widths = {col: len(str(col)) for col in cols}
    for row in display_rows:
        for col in cols:
            val = str(row.get(col, "NULL"))
            widths[col] = max(widths[col], min(len(val), 50))

    # Header
    header = " | ".join(str(col).ljust(widths[col]) for col in cols)
    # Separador no formato Header | Header \n ---+---
    separator = "-+-".join("-" * widths[col] for col in cols)
    
    lines = [header, separator]
    for row in display_rows:
        # Truncar valores muito longos para manter a tabela legível no log/console (o frontend lida com o wrap)
        line = " | ".join(str(row.get(col, "NULL"))[:50].ljust(widths[col]) for col in cols)
        lines.append(line)

    if max_rows is not None and len(rows) > max_rows:
        lines.append(f"... ({len(rows) - max_rows} linhas omitidas)")

    return "\n".join(lines)
