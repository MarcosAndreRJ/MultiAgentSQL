"""
Agent Registry: carrega e mantém todos os agentes configurados.
Lê arquivos YAML do diretório de configuração e instancia AgentConfig.
"""
from pathlib import Path
from typing import Optional

import yaml

from app.core.logger import get_logger
from app.core.settings import settings
from app.schemas.agent import AgentConfig, AgentGuards, AgentPermissions, AgentBehavior, DatabaseConfig

logger = get_logger("agent_registry")

# Registro em memória: {agent_id: AgentConfig}
_registry: dict[str, AgentConfig] = {}


def load_agents(config_dir: Optional[Path] = None) -> None:
    """
    Carrega todos os agentes do diretório de configuração.
    Deve ser chamado no startup da aplicação.
    """
    global _registry
    _registry = {}

    dir_path = config_dir or settings.agents_config_path
    if not dir_path.exists():
        logger.warning(f"Diretório de agentes não encontrado: {dir_path}")
        return

    yaml_files = list(dir_path.glob("*.yaml")) + list(dir_path.glob("*.yml"))
    if not yaml_files:
        logger.warning(f"Nenhum arquivo YAML de agente encontrado em: {dir_path}")
        return

    for yaml_file in yaml_files:
        try:
            _load_agent_file(yaml_file)
        except Exception as e:
            logger.error(f"Erro ao carregar agente de {yaml_file}: {e}")

    logger.info(f"Agentes carregados: {list(_registry.keys())}")


def _load_agent_file(yaml_file: Path) -> None:
    """Carrega um arquivo YAML de agente e registra no registry."""
    with open(yaml_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or "id" not in data:
        logger.warning(f"Arquivo YAML inválido ou sem 'id': {yaml_file}")
        return

    try:
        # Usa model_validate para que todos os validadores e defaults do Pydantic funcionem
        agent = AgentConfig.model_validate(data)
        _registry[agent.id] = agent
        logger.debug(f"Agente carregado: {agent.id} (tipo={agent.type})")
    except Exception as e:
        logger.error(f"Erro de validação no agente {yaml_file}: {e}")


def get(agent_id: str) -> Optional[AgentConfig]:
    """Busca um agente por ID."""
    return _registry.get(agent_id)


def get_all() -> list[AgentConfig]:
    """Retorna todos os agentes registrados."""
    return list(_registry.values())


def exists(agent_id: str) -> bool:
    """Verifica se um agente existe."""
    return agent_id in _registry


def reload_agents(config_dir: Optional[Path] = None) -> None:
    """Recarrega todos os agentes (sem reiniciar a aplicação)."""
    logger.info("Recarregando agentes...")
    load_agents(config_dir)


def add_skill_to_agent(agent_id: str, skill_id: str) -> bool:
    """
    Adiciona uma skill a um agente em runtime.
    Nota: não persiste no YAML — apenas no registry em memória.
    """
    agent = _registry.get(agent_id)
    if not agent:
        return False
    if skill_id not in agent.skills:
        agent.skills.append(skill_id)
        logger.info(f"Skill '{skill_id}' adicionada ao agente '{agent_id}'")
    return True


def remove_skill_from_agent(agent_id: str, skill_id: str) -> bool:
    """
    Remove uma skill de um agente em runtime.
    Nota: não persiste no YAML — apenas no registry em memória.
    """
    agent = _registry.get(agent_id)
    if not agent:
        return False
    if skill_id in agent.skills:
        agent.skills.remove(skill_id)
        logger.info(f"Skill '{skill_id}' removida do agente '{agent_id}'")
    return True
