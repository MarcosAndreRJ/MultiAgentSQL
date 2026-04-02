"""
Alias Resolver: módulo dedicado à resolução determinística de tokens @Alias.

Ponto único de entrada para resolução de aliases em qualquer parte do sistema.
Mantém a lógica de CRUD em alias_service.py e expõe aqui apenas funções de resolução,
facilitando testes isolados e uso em pipelines de processamento de mensagem.

Exportações principais:
  - resolve_message_aliases(agent_id, message) → (resolved_msg, alias_hits)
  - find_known_tokens(agent_id, message) → list[str]
  - find_unresolved_tokens(agent_id, message) → list[str]
"""
from __future__ import annotations

import re

from app.core.logger import get_logger
from app.services.alias_service import load_aliases
from app.services.alias_service import resolve_message_aliases  # re-export

logger = get_logger("alias_resolver")

__all__ = [
    "resolve_message_aliases",
    "find_known_tokens",
    "find_unresolved_tokens",
]

# Padrão de token @Alias
_TOKEN_RE = re.compile(r"@[A-Za-z_][A-Za-z0-9_]*")


def find_known_tokens(agent_id: str, message: str) -> list[str]:
    """
    Retorna os tokens @Alias presentes na mensagem que EXISTEM nos aliases
    do agente e, portanto, serão resolvidos por resolve_message_aliases.

    Útil para detectar quais tabelas o usuário mencionou explicitamente,
    antes mesmo de chamar a LLM.

    Exemplos:
        message = "quantos registros tem @Dicas e @Projeto"
        → ["@Dicas", "@Projeto"]  (se ambos existem para o agente)
    """
    data = load_aliases(agent_id)
    all_tokens = _TOKEN_RE.findall(message)
    if not all_tokens or data is None:
        return []
    combined_lower = {k.lower() for k in {**data.aliases, **data.manual_aliases}}
    return [t for t in all_tokens if t.lower() in combined_lower]


def find_unresolved_tokens(agent_id: str, message: str) -> list[str]:
    """
    Retorna os tokens @Alias presentes na mensagem que NÃO foram encontrados
    nos aliases do agente.

    Útil para sugerir ao usuário que o alias pode estar errado ou não cadastrado.

    Exemplos:
        message = "quantos registros @TabelaInexistente"
        → ["@TabelaInexistente"]
    """
    data = load_aliases(agent_id)
    all_tokens = _TOKEN_RE.findall(message)
    if not all_tokens:
        return []
    if data is None:
        return all_tokens
    combined_lower = {k.lower() for k in {**data.aliases, **data.manual_aliases}}
    return [t for t in all_tokens if t.lower() not in combined_lower]
