"""
Alias Service: gerencia aliases amigáveis para tabelas do banco de dados.

Responsabilidades:
- Gerar aliases automáticos a partir das tabelas do digest (@Tabela, @Tabelas)
- Carregar, mesclar e salvar aliases (automáticos + manuais)
- Resolver tokens @Alias em mensagens de forma determinística (sem LLM)
- manual_aliases têm prioridade sobre aliases automáticos

Estrutura do arquivo JSON:
{
  "agent_id": "mysql-example",
  "database": "devhacks_site",
  "generated_at": "...",
  "aliases": {"@Dica": "Dica", "@Dicas": "Dica", ...},
  "manual_aliases": {"@Hints": "Dica", ...}
}
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.core.logger import get_logger
from app.core.settings import settings
from app.schemas.digest import AliasData, DBDigest

logger = get_logger("alias_service")


# ─── Caminhos ─────────────────────────────────────────────────────────────────

def _aliases_path(agent_id: str) -> Path:
    return settings.aliases_path / f"{agent_id}.aliases.json"


# ─── Geração automática ───────────────────────────────────────────────────────

def generate_aliases_from_digest(digest: DBDigest) -> AliasData:
    """
    Gera aliases automáticos a partir das tabelas do digest e persiste.
    Preserva manual_aliases existentes se o arquivo já existir.
    """
    all_names = [t.name for t in digest.tables] + [v.name for v in digest.views]

    existing = _load_raw(digest.agent_id)
    manual = existing.get("manual_aliases", {}) if existing else {}

    auto_aliases: dict[str, str] = {}
    for name in all_names:
        for token in _generate_tokens(name):
            # Não sobrescrever se dois nomes geram mesmo token — primeiro ganha
            if token not in auto_aliases:
                auto_aliases[token] = name

    data = AliasData(
        agent_id=digest.agent_id,
        database=digest.database,
        generated_at=datetime.now(timezone.utc),
        aliases=auto_aliases,
        manual_aliases=manual,
    )

    _persist(data)
    logger.info(
        f"[ALIASES] Gerados {len(auto_aliases)} alias(es) automáticos "
        f"+ {len(manual)} manuais para agente={digest.agent_id}"
    )
    return data


def _generate_tokens(name: str) -> list[str]:
    """Gera lista de tokens para um nome de tabela (exato + plural simples)."""
    tokens = [f"@{name}"]  # exato
    plural = _simple_plural(name)
    if plural and plural.lower() != name.lower():
        tokens.append(f"@{plural}")
    return tokens


def _simple_plural(name: str) -> Optional[str]:
    """Heurística de plural em português/inglês sem biblioteca externa."""
    if not name:
        return None
    last = name[-1].lower()
    # Já termina em 's' — assume-se que já é plural ou invariável
    if last == "s":
        return None
    # Termina em vogal: adiciona 's'
    if last in "aeiouAEIOU":
        return name + "s"
    # Termina em consoante comum: adiciona 'es' se terminar em z, x; 's' para o resto
    if last in "zx":
        return name + "es"
    return name + "s"


# ─── Carga e persistência ─────────────────────────────────────────────────────

def load_aliases(agent_id: str) -> Optional[AliasData]:
    """Carrega aliases do arquivo JSON. Retorna None se não existir."""
    raw = _load_raw(agent_id)
    if raw is None:
        return None
    try:
        return AliasData.model_validate(raw)
    except Exception as e:
        logger.error(f"[ALIASES] Erro ao parsear aliases '{agent_id}': {e}")
        return None


def add_manual_alias(agent_id: str, alias: str, table_name: str) -> AliasData:
    """Adiciona ou sobrescreve um alias manual."""
    alias = _normalize_token(alias)
    data = load_aliases(agent_id) or AliasData(agent_id=agent_id, database="")
    data.manual_aliases[alias] = table_name
    _persist(data)
    logger.info(f"[ALIASES] Alias manual adicionado: {alias} → {table_name} (agente={agent_id})")
    return data


def remove_manual_alias(agent_id: str, alias: str) -> AliasData:
    """Remove um alias manual."""
    alias = _normalize_token(alias)
    data = load_aliases(agent_id) or AliasData(agent_id=agent_id, database="")
    removed = data.manual_aliases.pop(alias, None)
    if removed:
        logger.info(f"[ALIASES] Alias manual removido: {alias} (agente={agent_id})")
        _persist(data)
    else:
        logger.warning(f"[ALIASES] Alias manual não encontrado para remoção: {alias}")
    return data


def _persist(data: AliasData) -> None:
    path = _aliases_path(data.agent_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(data.model_dump_json(indent=2), encoding="utf-8")
    except Exception as e:
        logger.error(f"[ALIASES] Erro ao salvar aliases: {e}")
        raise


def _load_raw(agent_id: str) -> Optional[dict]:
    path = _aliases_path(agent_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"[ALIASES] Erro ao ler arquivo de aliases '{agent_id}': {e}")
        return None


# ─── Resolução de Aliases em Mensagens ────────────────────────────────────────

def resolve_message_aliases(
    agent_id: str,
    message: str,
) -> tuple[str, dict[str, str]]:
    """
    Resolve tokens @Alias na mensagem, retornando:
    - resolved_message: mensagem com tokens substituídos pelo nome real da tabela
    - alias_hits: mapeamento {token_original → nome_real} dos aliases resolvidos

    Prioridade: manual_aliases > aliases automáticos.
    Case-insensitive na busca, preserva casing original para aliases não encontrados.
    """
    data = load_aliases(agent_id)
    if data is None:
        return message, {}

    # Mapa unificado: manual tem prioridade
    combined: dict[str, str] = {}
    for token, name in data.aliases.items():
        combined[token.lower()] = name
    for token, name in data.manual_aliases.items():
        combined[token.lower()] = name

    if not combined:
        return message, {}

    alias_hits: dict[str, str] = {}

    # Regex para capturar strings com aspas OU tokens @Alias
    # Grupo 1: strings ("..." ou '...')
    # Grupo 2: tokens @Alias
    pattern = r"(\"[^\"]*\"|'[^']*')|(@[A-Za-z_][A-Za-z0-9_]*)"

    def _replace(match: re.Match) -> str:
        quoted = match.group(1)
        token = match.group(2)
        
        if quoted:
            return quoted # Retorna a string original sem mexer
        
        if token:
            key = token.lower()
            if key in combined:
                real_name = combined[key]
                alias_hits[token] = real_name
                return real_name
            return token
        return match.group(0)

    resolved = re.sub(pattern, _replace, message)

    if alias_hits:
        logger.debug(f"[ALIASES] Resolvidos: {alias_hits} | agente={agent_id}")

    return resolved, alias_hits


def suggest_aliases(agent_id: str, q: str = "") -> list[dict]:
    """
    Retorna sugestões de aliases filtradas por um prefixo `q` (case-insensitive).
    Mescla aliases manuais e automáticos, retornando uma lista ordenada onde
    aliases manuais têm prioridade.

    Formato de retorno:
    [
        {"alias": "@token", "table": "NomeTabela", "source": "manual"},
        {"alias": "@tokens", "table": "NomeTabela", "source": "auto"}
    ]
    """
    data = load_aliases(agent_id)
    if data is None:
        return []

    q_lower = q.lower()
    results = []
    
    # 1. Manuais (Prioridade)
    for token, name in data.manual_aliases.items():
        if token.lower().startswith(q_lower):
            results.append({
                "alias": token,
                "table": name,
                "source": "manual"
            })
            
    # Criar um set de tokens já adicionados para evitar duplicatas manuais vs autos
    added_tokens = {r["alias"].lower() for r in results}

    # 2. Automáticos
    for token, name in data.aliases.items():
        if token.lower() not in added_tokens and token.lower().startswith(q_lower):
            results.append({
                "alias": token,
                "table": name,
                "source": "auto"
            })
            added_tokens.add(token.lower())

    # Ordenar alfa dentro de suas categorias
    # Já estão essencialmente agrupados por manual primeiro, mas podemos
    # ordenar pelo nome do alias dentro dos grupos
    results.sort(key=lambda x: (
        0 if x["source"] == "manual" else 1,
        x["alias"].lower()
    ))

    return results


def _normalize_token(token: str) -> str:
    """Garante que o token começa com @."""
    token = token.strip()
    if not token.startswith("@"):
        token = f"@{token}"
    return token
