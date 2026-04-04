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


def serialize_database_binding_for_output(binding) -> dict:
    """Serializa um objeto AgentDatabaseBinding ORM ou dict para saída segura.

    Não inclui o password, apenas indica se existe via has_password.
    """
    # binding pode ser ORM ou dict-like
    try:
        has_password = bool(getattr(binding, "password", None))
    except Exception:
        has_password = bool(binding.get("password")) if isinstance(binding, dict) else False

    return {
        "id": getattr(binding, "id", None) or binding.get("id") if isinstance(binding, dict) else None,
        "agent_id": getattr(binding, "agent_id", None) or binding.get("agent_id") if isinstance(binding, dict) else None,
        "db_type": getattr(binding, "db_type", None) or binding.get("db_type") if isinstance(binding, dict) else None,
        "host": getattr(binding, "host", None) or binding.get("host") if isinstance(binding, dict) else None,
        "port": getattr(binding, "port", None) or binding.get("port") if isinstance(binding, dict) else None,
        "database_name": getattr(binding, "database_name", None) or binding.get("database_name") if isinstance(binding, dict) else None,
        "schema_name": getattr(binding, "schema_name", None) or binding.get("schema_name") if isinstance(binding, dict) else None,
        "username": getattr(binding, "username", None) or binding.get("username") if isinstance(binding, dict) else None,
        "connection_label": getattr(binding, "connection_label", None) or binding.get("connection_label") if isinstance(binding, dict) else None,
        "is_active": getattr(binding, "is_active", None) or binding.get("is_active") if isinstance(binding, dict) else None,
        "is_default": getattr(binding, "is_default", None) or binding.get("is_default") if isinstance(binding, dict) else None,
        "read_only": getattr(binding, "read_only", None) or binding.get("read_only") if isinstance(binding, dict) else None,
        "has_password": has_password,
        "created_at": getattr(binding, "created_at", None) or binding.get("created_at") if isinstance(binding, dict) else None,
        "updated_at": getattr(binding, "updated_at", None) or binding.get("updated_at") if isinstance(binding, dict) else None,
    }
