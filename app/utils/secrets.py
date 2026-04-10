"""
Helpers para mascaramento/serializacao de campos sensiveis.
"""
from typing import Optional


def mask_secret(value: Optional[str]) -> str:
    """Mascara um valor sensível para exibicao.

    Regras simples: None -> 'NOT_SET'; curta -> '****'; longa -> prefix/suffix.
    """
    if not value:
        return "NOT_SET"
    if len(value) <= 4:
        return "****"
    if len(value) <= 8:
        return f"{value[0]}***{value[-1]}"
    return f"{value[:4]}...{value[-4:]}"


def mask_api_key_for_logs(api_key: Optional[str]) -> str:
    """Mascara uma api_key para logs (garante que nao vazem no logger).

    Exemplo: sk-1234567890 -> sk-****7890
    """
    if not api_key:
        return "<NOT_SET>"
    if len(api_key) <= 8:
        return "****"
    # tenta preservar prefixes como sk-
    prefix = api_key.split("-")[0] if "-" in api_key else ""
    suffix = api_key[-4:]
    if prefix:
        return f"{prefix}-****{suffix}"
    return f"****{suffix}"


