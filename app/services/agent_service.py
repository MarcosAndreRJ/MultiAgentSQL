"""
Agent Service: operações sobre agentes (listagem, detalhes, status de conexão).
"""
from typing import Optional, List
import uuid
import yaml
from pathlib import Path

from app.core import agent_registry
from app.core.logger import get_logger
from app.core.settings import settings
from app.schemas.agent import AgentSummary, AgentDetail, AgentCreate, DatabaseConfig
from app.db.session import SessionLocal
from app.db import models as db_models
from sqlalchemy import text
import time

logger = get_logger("agent_service")


async def create_agent(data: AgentCreate, db_session: Optional[SessionLocal] = None) -> AgentSummary:
    """
    Cria um novo agente:
    1. Gera ID único
    2. Cria arquivo YAML em config/agents/
    3. Recarrega o agent_registry
    4. Cria binding de banco se dados informados
    """
    agent_id = f"agent_{uuid.uuid4().hex[:8]}"
    
    agent_config = {
        "id": agent_id,
        "name": data.name,
        "description": data.description,
        "type": data.type,
        "model": data.model,
        "prompt_file": data.prompt_file,
        "skills": [],
        "permissions": {
            "can_read_db": True,
            "can_write_db": False,
            "can_ddl": False,
            "can_execute": False,
            "protected_tables": []
        },
        "guards": {
            "require_confirmation_for": ["DELETE", "DROP", "TRUNCATE"],
            "auto_approve": ["SELECT", "SHOW", "DESCRIBE"]
        },
        "behavior": {
            "max_loop_steps": 3,
            "response_style": "technical",
            "language": "pt-BR",
            "max_result_rows": 500,
            "introspect_before_ddl": True
        }
    }
    
    if data.database:
        agent_config["database"] = {
            "host": data.database.host,
            "port": data.database.port,
            "name": data.database.name,
            "user": data.database.user,
            "password": data.database.password,
            "connect_timeout": data.database.connect_timeout,
            "pool_size": data.database.pool_size
        }
    
    agents_dir = Path(settings.AGENTS_CONFIG_DIR)
    agents_dir.mkdir(parents=True, exist_ok=True)
    
    yaml_path = agents_dir / f"{agent_id}.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(agent_config, f, default_flow_style=False, allow_unicode=True)
    
    logger.info(f"Arquivo YAML criado: {yaml_path}")
    
    agent_registry.reload_agents()
    
    new_agent = agent_registry.get(agent_id)
    if not new_agent:
        raise Exception("Falha ao carregar agente após criação")
    
    if db_session and data.database:
        try:
            binding = db_models.AgentDatabaseBinding(
                agent_id=agent_id,
                db_type="mysql",
                host=data.database.host,
                port=data.database.port,
                database_name=data.database.name,
                schema_name=None,
                username=data.database.user,
                password=data.database.password,
                connection_label="default",
                is_active=True,
                is_default=True,
                read_only=True
            )
            db_session.add(binding)
            db_session.commit()
            logger.info(f"Binding de banco criado para agente {agent_id}")
        except Exception as e:
            logger.warning(f"Banco configurado no YAML mas binding não criado: {e}")
    
    return AgentSummary(
        id=new_agent.id,
        name=new_agent.name,
        description=new_agent.description,
        type=new_agent.type,
        model=new_agent.model,
        database_name=new_agent.database.name if new_agent.database else None,
        skills=new_agent.skills,
        is_online=True
    )


async def list_agents() -> list[AgentSummary]:
    """Lista todos os agentes com informações resumidas."""
    agents = agent_registry.get_all()
    summaries = []
    
    for config in agents:
        summary = AgentSummary(
            id=config.id,
            name=config.name,
            description=config.description,
            type=config.type,
            model=config.model,
            database_name=config.database.name if config.database else None,
            skills=config.skills,
            is_online=True,
        )
        summaries.append(summary)
    
    return summaries


async def get_agent_detail(agent_id: str) -> Optional[AgentDetail]:
    """Retorna detalhes completos de um agente."""
    config = agent_registry.get(agent_id)
    if not config:
        return None

    from app.agents.prompt_builder import load_base_prompt
    try:
        prompt_preview = load_base_prompt(config)[:500] + "..." if len(load_base_prompt(config)) > 500 else load_base_prompt(config)
    except Exception:
        prompt_preview = None

    return AgentDetail(
        id=config.id,
        name=config.name,
        description=config.description,
        type=config.type,
        model=config.model,
        database_name=config.database.name if config.database else None,
        skills=config.skills,
        is_online=True,
        prompt_preview=prompt_preview,
        permissions=config.permissions,
        guards=config.guards,
        behavior=config.behavior,
    )


async def test_agent_target_db_connection(agent_id: str) -> dict:
    """
    Testa a conexão SQL REAL do banco operacional (target_db) de um agente.
    """
    db = SessionLocal()
    start_time = time.time()
    
    try:
        from app.services.target_db.connection_manager import connection_manager
        
        engine = connection_manager.get_engine(db, agent_id)
        
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            latency = (time.time() - start_time) * 1000
            
            logger.info(f"Target DB Saudável | Agente: {agent_id} | Latência: {round(latency, 2)}ms")
            
            return {
                "status": "ok",
                "latency_ms": round(latency, 2),
                "agent_id": agent_id,
                "domain": "target_db",
                "error": None
            }
            
    except Exception as e:
        latency = (time.time() - start_time) * 1000
        logger.error(f"Target DB Offline | Agente: {agent_id} | Erro: {str(e)}")
        
        return {
            "status": "error",
            "latency_ms": round(latency, 2),
            "agent_id": agent_id,
            "domain": "target_db",
            "error": str(e)
        }
    finally:
        db.close()