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
    OBSOLETO: Agentes agora são carregados sob demanda do Banco de Dados.
    Mantido para compatibilidade de assinatura, mas não lê mais YAML.
    """
    logger.info("Agent Registry: Governança via Banco de Dados ATIVA. Ignorando arquivos YAML.")


def get(agent_id: str) -> Optional[AgentConfig]:
    """Busca um agente por ID no Banco de Dados (Plataforma)."""
    from app.db.session import SessionLocal
    from app.services.platform import agent_governance_service
    
    db = SessionLocal()
    try:
        return agent_governance_service.resolve_full_agent(db, agent_id)
    except Exception as e:
        logger.error(f"Erro ao resolver agente '{agent_id}' via Registro/DB: {e}")
        return None
    finally:
        db.close()


def get_all() -> list[AgentConfig]:
    """Retorna todos os agentes ativos registrados no banco."""
    from app.db.session import SessionLocal
    from app.db import models as db_models
    from app.services.platform import agent_governance_service
    
    db = SessionLocal()
    try:
        ids = db.query(db_models.Agent.id).filter(db_models.Agent.is_active == True).all()
        agents = []
        for (aid,) in ids:
            config = agent_governance_service.resolve_full_agent(db, aid)
            if config:
                agents.append(config)
        return agents
    except Exception as e:
        logger.error(f"Erro ao listar todos os agentes via Registro/DB: {e}")
        return []
    finally:
        db.close()


def exists(agent_id: str) -> bool:
    """Verifica se um agente existe no banco."""
    from app.db.session import SessionLocal
    from app.db import models as db_models
    
    db = SessionLocal()
    try:
        return db.query(db_models.Agent).filter(db_models.Agent.id == agent_id).first() is not None
    finally:
        db.close()


def reload_agents(config_dir: Optional[Path] = None) -> None:
    """OBSOLETO: Agentes são governados pelo banco. Recarga não é mais necessária para arquivos."""
    logger.info("Recarregando cache de governança (operação vazia).")


def add_skill_to_agent(agent_id: str, skill_id: str) -> bool:
    """
    Adiciona uma skill a um agente no banco de dados.
    """
    from app.db.session import SessionLocal
    from app.db import models as db_models
    import json
    
    db = SessionLocal()
    try:
        agent = db.query(db_models.Agent).filter(db_models.Agent.id == agent_id).first()
        if not agent:
            return False
            
        skills = json.loads(agent.skills_json) if agent.skills_json else []
        if skill_id not in skills:
            skills.append(skill_id)
            agent.skills_json = json.dumps(skills)
            db.commit()
            logger.info(f"Skill '{skill_id}' adicionada ao agente '{agent_id}' no banco.")
        return True
    except Exception as e:
        logger.error(f"Erro ao adicionar skill via Registro/DB: {e}")
        return False
    finally:
        db.close()


def remove_skill_from_agent(agent_id: str, skill_id: str) -> bool:
    """
    Remove uma skill de um agente no banco de dados.
    """
    from app.db.session import SessionLocal
    from app.db import models as db_models
    import json
    
    db = SessionLocal()
    try:
        agent = db.query(db_models.Agent).filter(db_models.Agent.id == agent_id).first()
        if not agent:
            return False
            
        skills = json.loads(agent.skills_json) if agent.skills_json else []
        if skill_id in skills:
            skills.remove(skill_id)
            agent.skills_json = json.dumps(skills)
            db.commit()
            logger.info(f"Skill '{skill_id}' removida do agente '{agent_id}' no banco.")
        return True
    except Exception as e:
        logger.error(f"Erro ao remover skill via Registro/DB: {e}")
        return False
    finally:
        db.close()
