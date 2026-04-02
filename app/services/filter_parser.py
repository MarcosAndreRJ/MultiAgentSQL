"""
Filter Parser: extrai filtros de linguagem natural para estrutura tipada.

Responsabilidades:
- Detectar pares campo/valor em linguagem natural (PT-BR e EN)
- Detectar operadores relacionais (=, >, <, >=, <=, LIKE, IS NULL)
- Detectar limite de linhas
- Detectar ordenação
- Retornar slots normalizados sem SQL — a geração de SQL fica no query_builder

Nunca interpreta nomes de coluna como literais SQL — apenas extrai
o que o usuário disse; a validação contra o digest fica no v2_service.

Exemplos de inputs suportados:
  "status ativo"                  → Filter(field="status", op="=", value="ativo")
  "id > 10"                       → Filter(field="id", op=">", value=10)
  "nome contém joao"              → Filter(field="nome", op="LIKE", value="%joao%")
  "cidade = Recife"               → Filter(field="cidade", op="=", value="Recife")
  "status não é inativo"          → Filter(field="status", op="!=", value="inativo")
  "descricao like abc"            → Filter(field="descricao", op="LIKE", value="%abc%")
  "10 primeiros"                  → Limit(10)
  "limite 20"                     → Limit(20)
  "ordenado por nome"             → OrderBy(field="nome", direction="asc")
  "por id desc"                   → OrderBy(field="id", direction="desc")
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional, Union


# ─── Estruturas de dados ──────────────────────────────────────────────────────

@dataclass
class QueryFilter:
    """Um filtro simples: campo op valor."""
    field: str
    op: str     # "=" | "!=" | ">" | "<" | ">=" | "<=" | "LIKE" | "IS NULL" | "IS NOT NULL"
    value: Union[str, int, float, None]

    def to_dict(self) -> dict:
        return {"field": self.field, "op": self.op, "value": self.value}


@dataclass
class OrderByClause:
    """Cláusula de ordenação."""
    field: str
    direction: str = "asc"  # "asc" | "desc"

    def to_dict(self) -> dict:
        return {"field": self.field, "direction": self.direction}


@dataclass
class ParsedSlots:
    """Slots extraídos de uma mensagem natural."""
    filters: list[QueryFilter] = field(default_factory=list)
    order_by: list[OrderByClause] = field(default_factory=list)
    limit: Optional[int] = None
    raw_remainder: str = ""  # parte da mensagem que não foi parseada

    def to_dict(self) -> dict:
        return {
            "filters": [f.to_dict() for f in self.filters],
            "order_by": [o.to_dict() for o in self.order_by],
            "limit": self.limit,
            "raw_remainder": self.raw_remainder,
        }


# ─── Constantes de regex ──────────────────────────────────────────────────────

# Identificador: letras, dígitos, underscore — começa com letra/underscore
_IDENT = r'[A-Za-z_][A-Za-z0-9_]*'

# Valor literal: string sem espaço, número, "texto com espaço" entre aspas
_VALUE_BARE = r"""(?:"[^"]*"|'[^']*'|[\w\-\.]+)"""

# Operadores PT-BR / SQL mapeados para operador canônico
_OP_MAP: dict[str, str] = {
    "=": "=", "!=": "!=", "<>": "!=",
    ">=": ">=", "<=": "<=", ">": ">", "<": "<",
    "é": "=", "igual": "=", "igual a": "=",
    "não é": "!=", "diferente de": "!=", "diferente": "!=",
    "maior que": ">", "maior": ">",
    "menor que": "<", "menor": "<",
    "maior ou igual": ">=", "maior ou igual a": ">=",
    "menor ou igual": "<=", "menor ou igual a": "<=",
    "contém": "LIKE", "contain": "LIKE",
    "like": "LIKE", "parecido": "LIKE",
    "nulo": "IS NULL", "null": "IS NULL", "vazio": "IS NULL",
    "não nulo": "IS NOT NULL", "not null": "IS NOT NULL",
    "não vazio": "IS NOT NULL",
}

# Palavras de ignoring (stop-words para extração de filtros)
_STOP_WORDS = frozenset({
    "a", "as", "o", "os", "de", "do", "da", "dos", "das",
    "para", "com", "que", "na", "no", "em", "e", "ou",
    "onde", "when", "with", "from", "the", "and", "or",
    "me", "mostre", "liste", "traga", "quero", "ver", "mostrar",
    "listar", "selecione", "selecionar", "exibir", "exiba",
    "registros", "tabela", "campo", "coluna", "todos", "todas", "todo",
})

# Regex composta para ORDER BY
_ORDER_RE = re.compile(
    r'\b(?:ordenad[oa]s?\s+por|order\s+by|por|sorted?\s+by)\s+'
    rf'(?P<field>{_IDENT})'
    r'(?:\s+(?P<dir>asc|desc|ascendente|descendente|crescente|decrescente))?\b',
    re.IGNORECASE,
)

# Regex para LIMIT
_LIMIT_RE = re.compile(
    r'\b(?:'
    r'(?P<n1>\d+)\s+(?:primeiros?|\u00faltimos?|registros?|linhas?|itens?)|'  # "10 primeiros"
    r'(?:limite|limit|m[aá]ximo|max|top)\s+(?P<n2>\d+)|'                     # "limite 20"
    r'(?:at[eé]\s+)?(?P<n3>\d+)\s+(?:resultado|resultados|linhas?)'          # "até 10 resultados"
    r')\b',
    re.IGNORECASE,
)

# Regex para filtros com operadores explícitos (campo op valor)
_FILTER_OP_EXPLICIT = re.compile(
    rf'\b(?P<field>{_IDENT})\s*'
    r'(?P<op>>=|<=|!=|<>|>|<|=)\s*'
    rf'(?P<value>{_VALUE_BARE})',
    re.IGNORECASE,
)

# Regex para " campo operador_textual valor "
_FILTER_OP_TEXT = re.compile(
    rf'\b(?P<field>{_IDENT})\s+'
    r'(?P<op>não é|diferente de|maior ou igual a|menor ou igual a|maior ou igual|menor ou igual|'
    r'maior que|menor que|maior|menor|igual a|igual|não nulo|não vazio|'
    r'nulo|vazio|not null|is not null|is null|'
    r'contém|contain|like|parecido|é)\s*'
    rf'(?P<value>{_VALUE_BARE})?',
    re.IGNORECASE | re.UNICODE,
)

# Regex para "campo valor" simples (sem operador — assume =)
_FILTER_PLAIN = re.compile(
    rf'\b(?P<field>{_IDENT})\s+(?P<value>[A-Za-z][A-Za-z0-9_\-]*)\b',
    re.IGNORECASE,
)


# ─── Funções públicas ─────────────────────────────────────────────────────────

def parse_slots(text: str) -> ParsedSlots:
    """
    Extrai filtros, ordenação e limite de uma string de linguagem natural.

    Args:
        text: Mensagem com aliases já resolvidos, sem @token.

    Returns:
        ParsedSlots com campos normalizados.
    """
    slots = ParsedSlots()
    work = text

    # 1. ORDER BY — extrair e remover do texto de trabalho
    work, order_clauses = _extract_order_by(work)
    slots.order_by = order_clauses

    # 2. LIMIT — extrair e remover
    work, limit = _extract_limit(work)
    slots.limit = limit

    # 3. Filtros com operador explícito (campo >= valor)
    work, explicit_filters = _extract_explicit_filters(work)
    slots.filters.extend(explicit_filters)

    # 4. Filtros com operador textual ("campo contém valor")
    work, text_filters = _extract_text_op_filters(work)
    slots.filters.extend(text_filters)

    slots.raw_remainder = work.strip()
    return slots


def parse_limit_from_text(text: str) -> Optional[int]:
    """Extrai somente o limite de um texto. Conveniente para callers simples."""
    m = _LIMIT_RE.search(text)
    if not m:
        return None
    n = m.group("n1") or m.group("n2") or m.group("n3")
    return int(n) if n else None


def parse_order_from_text(text: str) -> list[OrderByClause]:
    """Extrai somente as cláusulas ORDER BY de um texto."""
    _, clauses = _extract_order_by(text)
    return clauses


# ─── Funções internas ─────────────────────────────────────────────────────────

def _extract_order_by(text: str) -> tuple[str, list[OrderByClause]]:
    clauses: list[OrderByClause] = []
    consumed_spans: list[tuple[int, int]] = []

    for m in _ORDER_RE.finditer(text):
        f = m.group("field")
        d_raw = (m.group("dir") or "asc").lower()
        direction = "desc" if d_raw in ("desc", "descendente", "decrescente") else "asc"
        clauses.append(OrderByClause(field=f, direction=direction))
        consumed_spans.append((m.start(), m.end()))

    work = _remove_spans(text, consumed_spans)
    return work, clauses


def _extract_limit(text: str) -> tuple[str, Optional[int]]:
    m = _LIMIT_RE.search(text)
    if not m:
        return text, None
    n = m.group("n1") or m.group("n2") or m.group("n3")
    limit = int(n) if n else None
    work = text[:m.start()] + text[m.end():]
    return work.strip(), limit


def _extract_explicit_filters(text: str) -> tuple[str, list[QueryFilter]]:
    """Extrai filtros com operadores simbólicos: campo >= valor, campo = 'x'."""
    filters: list[QueryFilter] = []
    consumed_spans: list[tuple[int, int]] = []

    for m in _FILTER_OP_EXPLICIT.finditer(text):
        field = m.group("field").strip()
        if field.lower() in _STOP_WORDS:
            continue
        op_raw = m.group("op").strip()
        op = _OP_MAP.get(op_raw, op_raw)
        value = _parse_value(m.group("value"))
        filters.append(QueryFilter(field=field, op=op, value=value))
        consumed_spans.append((m.start(), m.end()))

    work = _remove_spans(text, consumed_spans)
    return work, filters


def _extract_text_op_filters(text: str) -> tuple[str, list[QueryFilter]]:
    """Extrai filtros com operadores textuais: 'campo contém valor', 'campo é Y'."""
    filters: list[QueryFilter] = []
    consumed_spans: list[tuple[int, int]] = []

    for m in _FILTER_OP_TEXT.finditer(text):
        field = m.group("field").strip()
        if field.lower() in _STOP_WORDS:
            continue
        op_raw = m.group("op").strip().lower()
        op = _OP_MAP.get(op_raw)
        if op is None:
            continue

        value_raw = m.group("value") if m.group("value") else None
        value = _parse_value(value_raw) if value_raw else None

        # Para IS NULL / IS NOT NULL o valor não é necessário
        if op in ("IS NULL", "IS NOT NULL"):
            filters.append(QueryFilter(field=field, op=op, value=None))
        elif value is not None:
            if op == "LIKE":
                value = f"%{value}%"
            filters.append(QueryFilter(field=field, op=op, value=value))
        else:
            continue

        consumed_spans.append((m.start(), m.end()))

    work = _remove_spans(text, consumed_spans)
    return work, filters


def _parse_value(raw: str) -> Union[str, int, float]:
    """Remove quotes e converte para tipo numérico se possível."""
    if raw is None:
        return None
    v = raw.strip().strip("'\"")
    # Tentar int
    try:
        return int(v)
    except ValueError:
        pass
    # Tentar float
    try:
        return float(v)
    except ValueError:
        pass
    return v


def _remove_spans(text: str, spans: list[tuple[int, int]]) -> str:
    """Remove intervalos do texto e colapsa espaços extras."""
    if not spans:
        return text
    result = []
    prev = 0
    for start, end in sorted(spans):
        result.append(text[prev:start])
        prev = end
    result.append(text[prev:])
    return re.sub(r'\s{2,}', ' ', " ".join(result)).strip()
