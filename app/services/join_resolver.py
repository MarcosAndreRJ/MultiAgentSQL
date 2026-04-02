"""
Join Resolver: resolve caminhos de JOIN usando as FKs do DB Digest.

Responsabilidades:
- Dado um digest e dois nomes de tabela, encontrar um caminho direto de JOIN
  consultando as foreign keys do digest
- Suportar caminhos diretos (A→B via FK) e caminhos reversos (B→A)
- Retornar um JoinPath com confiança alta somente se a FK for direta e única
- Retornar None se nenhum caminho for encontrado ou ambíguo

Design de segurança:
- Todos os nomes são validados contra o digest: nenhum nome externo é
  aceito sem confirmação de que existe uma tabela/coluna real no banco
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from app.schemas.digest import DBDigest, TableDigest

logger = logging.getLogger(__name__)


# ─── Estruturas de dados ──────────────────────────────────────────────────────

@dataclass
class JoinPath:
    """Descreve um único caminho de JOIN entre duas tabelas."""
    left_table: str
    right_table: str
    left_col: str
    right_col: str
    # "direct"   = FK em left_table → right_table
    # "reverse"  = FK em right_table → left_table
    direction: str
    confidence: float  # 1.0 = FK direta encontrada; 0.0 = nenhum caminho

    def to_dict(self) -> dict:
        return {
            "left_table": self.left_table,
            "right_table": self.right_table,
            "left_col": self.left_col,
            "right_col": self.right_col,
            "direction": self.direction,
            "confidence": self.confidence,
        }


# ─── API pública ───────────────────────────────────────────────────────────────

def resolve_join(
    digest: DBDigest,
    left_table: str,
    right_table: str,
) -> Optional[JoinPath]:
    """
    Tenta encontrar um caminho de JOIN direto entre left_table e right_table.

    Retorna None se:
    - Alguma das tabelas não existe no digest
    - Nenhuma FK liga as duas tabelas
    - Há mais de um caminho possível (ambíguo → fallback para LLM)

    Args:
        digest: DBDigest já carregado para o agente.
        left_table: Nome da tabela "principal" (lado esquerdo).
        right_table: Nome da tabela "relacionada" (lado direito).

    Returns:
        JoinPath com confidence=1.0 se único e direto, ou None.
    """
    all_tables = _build_table_index(digest)

    left_td = all_tables.get(left_table.lower())
    right_td = all_tables.get(right_table.lower())

    if left_td is None or right_td is None:
        logger.debug(
            "[join_resolver] tabela não encontrada no digest: %s / %s",
            left_table,
            right_table,
        )
        return None

    paths: list[JoinPath] = []

    # Direção direta: FK em left_td referenciando right_td
    for fk in left_td.foreign_keys:
        if fk.ref_table.lower() == right_td.name.lower():
            paths.append(
                JoinPath(
                    left_table=left_td.name,
                    right_table=right_td.name,
                    left_col=fk.column,
                    right_col=fk.ref_column,
                    direction="direct",
                    confidence=1.0,
                )
            )

    # Direção reversa: FK em right_td referenciando left_td
    for fk in right_td.foreign_keys:
        if fk.ref_table.lower() == left_td.name.lower():
            paths.append(
                JoinPath(
                    left_table=left_td.name,
                    right_table=right_td.name,
                    left_col=fk.ref_column,
                    right_col=fk.column,
                    direction="reverse",
                    confidence=1.0,
                )
            )

    if not paths:
        logger.debug(
            "[join_resolver] nenhuma FK encontrada entre %s e %s",
            left_table,
            right_table,
        )
        return None

    if len(paths) > 1:
        logger.debug(
            "[join_resolver] %d caminhos ambíguos entre %s e %s — fallback",
            len(paths),
            left_table,
            right_table,
        )
        return None  # ambíguo → delega ao LLM

    return paths[0]


def find_join_chain(
    digest: DBDigest,
    tables: list[str],
) -> Optional[list[JoinPath]]:
    """
    Resolve uma cadeia de JOINs para uma lista de tabelas (mínimo 2).

    Cada par consecutivo de tabelas deve ter um JoinPath viável.
    Se qualquer par for ambíguo ou inexistente, retorna None.

    Args:
        digest: DBDigest do agente.
        tables: Lista ordenada de nomes de tabela.

    Returns:
        Lista de JoinPath (len = len(tables) - 1), ou None se não resolvível.
    """
    if len(tables) < 2:
        return []

    chain: list[JoinPath] = []
    for i in range(len(tables) - 1):
        jp = resolve_join(digest, tables[i], tables[i + 1])
        if jp is None:
            return None
        chain.append(jp)

    return chain


def table_exists_in_digest(digest: DBDigest, table_name: str) -> bool:
    """Verifica se uma tabela (ou view) existe no digest."""
    idx = _build_table_index(digest)
    return table_name.lower() in idx


def get_table_from_digest(digest: DBDigest, table_name: str) -> Optional[TableDigest]:
    """Retorna o TableDigest pelo nome (case-insensitive), ou None."""
    return _build_table_index(digest).get(table_name.lower())


# ─── Helpers internos ─────────────────────────────────────────────────────────

def _build_table_index(digest: DBDigest) -> dict[str, TableDigest]:
    """Constrói um índice {nome_lower: TableDigest} de tabelas + views."""
    index: dict[str, TableDigest] = {}
    for td in digest.tables:
        index[td.name.lower()] = td
    for vd in digest.views:
        index[vd.name.lower()] = vd
    return index
