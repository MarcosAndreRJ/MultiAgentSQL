"""
Serviço de Governança de Agentes (Platform DB).
Resolve a configuração efetiva de runtime priorizando o banco de dados.
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from pydantic import BaseModel
import json

from app.db import models as db_models
from app.core import agent_registry
from app.core.logger import get_logger

from app.schemas.agent import (
    AgentConfig, AgentPermissions, AgentGuards, 
    AgentBehavior, DatabaseConfig, AgentLLMConfig
)

logger = get_logger("governance.service")

class AgentRuntimeConfig(BaseModel):
    # ... (mantém os campos anteriores para compatibilidade interna se necessário)
    agent_id: str
    agent_name: str
    is_active: bool
    source: str  # 'platform_db' | 'yaml_fallback'
    
    # LLM
    llm_provider_id: Optional[int] = None
    llm_provider_name: Optional[str] = None
    llm_model_id: Optional[int] = None
    llm_model_identifier: Optional[str] = None
    llm_binding_active: bool = False
    
    # Database
    db_connection_id: Optional[int] = None
    db_connection_name: Optional[str] = None
    db_host: Optional[str] = None
    db_binding_active: bool = False
    
    # Flags administrativas (serializadas)
    permissions: Optional[dict] = None
    guards: Optional[dict] = None
    behavior: Optional[dict] = None
    icon: Optional[str] = "🤖"
    
    warnings: List[str] = []

def resolve_full_agent(db: Session, agent_id: str) -> Optional[AgentConfig]:
    """
    Resolve a configuração completa de um agente a partir do banco de dados.
    Substitui a necessidade de ler arquivos YAML em runtime.
    """
    agent_record = db.query(db_models.Agent).filter(db_models.Agent.id == agent_id).first()
    if not agent_record:
        return None
    
    # 1. Resolve LLM Binding (Primário)
    llm_binding = db.query(db_models.AgentLLMBinding).filter(
        db_models.AgentLLMBinding.agent_id == agent_id,
        db_models.AgentLLMBinding.is_primary == True,
        db_models.AgentLLMBinding.is_active == True
    ).first()
    
    model_name = "llama3" # Fallback super básico
    llm_config = None
    if llm_binding:
        model_name = llm_binding.model.model_identifier
        llm_config = AgentLLMConfig(
            provider=llm_binding.provider.provider_type,
            model=llm_binding.model.model_identifier,
            base_url=llm_binding.provider.base_url
        )

    # 2. Resolve Database Config (Privilegia V2, fallback V1)
    db_config = None
    
    # Tenta V2 (normalizado)
    db_binding_v2 = db.query(db_models.AgentDatabaseBindingV2).filter(
        db_models.AgentDatabaseBindingV2.agent_id == agent_id,
        db_models.AgentDatabaseBindingV2.is_primary == True,
        db_models.AgentDatabaseBindingV2.is_active == True
    ).first()
    
    if db_binding_v2:
        conn = db.query(db_models.DatabaseConnection).filter(db_models.DatabaseConnection.id == db_binding_v2.database_connection_id).first()
        if conn:
            db_config = DatabaseConfig(
                host=conn.host,
                port=conn.port,
                name=conn.database_name,
                user=conn.username,
                password=conn.password_encrypted
            )
    else:
        # Tenta V1 (legado, mas persistido no DB)
        db_binding_v1 = db.query(db_models.AgentDatabaseBinding).filter(
            db_models.AgentDatabaseBinding.agent_id == agent_id,
            db_models.AgentDatabaseBinding.is_active == True
        ).first()
        if db_binding_v1:
            db_config = DatabaseConfig(
                host=db_binding_v1.host,
                port=db_binding_v1.port,
                name=db_binding_v1.database_name,
                user=db_binding_v1.username,
                password=db_binding_v1.password
            )

    # 3. Construir AgentConfig (Pydantic)
    try:
        return AgentConfig(
            id=agent_record.id,
            name=agent_record.name,
            description=agent_record.description or "",
            type=agent_record.agent_type,
            model=model_name,
            icon=agent_record.icon or "🤖",
            prompt_file=agent_record.prompt_file or "base.txt",
            skills=json.loads(agent_record.skills_json) if agent_record.skills_json else [],
            database=db_config,
            permissions=AgentPermissions.model_validate(json.loads(agent_record.permissions_json)) if agent_record.permissions_json else AgentPermissions(),
            guards=AgentGuards.model_validate(json.loads(agent_record.guards_json)) if agent_record.guards_json else AgentGuards(),
            behavior=AgentBehavior.model_validate(json.loads(agent_record.behavior_json)) if agent_record.behavior_json else AgentBehavior(),
            llm=llm_config
        )
    except Exception as e:
        logger.error(f"Erro ao validar AgentConfig do banco para '{agent_id}': {e}")
        return None

def resolve_agent_runtime_config(db: Session, agent_id: str) -> AgentRuntimeConfig:
    """
    Resolve a configuração efetiva de runtime para um agente. (Versão resumida para UI/Flags)
    """
    agent_record = db.query(db_models.Agent).filter(db_models.Agent.id == agent_id).first()
    
    # Se existe no banco, resolve as amarrações
    if agent_record:
        return _resolve_from_db(db, agent_record)
    
    # Fallback super controlado apenas se não estiver no banco (Bootstrap pendente)
    yaml_config = agent_registry.get(agent_id)
    if yaml_config:
        logger.warning(f"Agent '{agent_id}' ausente no DB Governança. Usando fallback YAML.")
        return AgentRuntimeConfig(
            agent_id=yaml_config.id,
            agent_name=yaml_config.name,
            is_active=True,
            source="yaml_fallback",
            permissions=yaml_config.permissions.model_dump() if yaml_config.permissions else {},
            guards=yaml_config.guards.model_dump() if yaml_config.guards else {},
            behavior=yaml_config.behavior.model_dump() if yaml_config.behavior else {},
            warnings=["Fallback YAML ativo. Agente não governado pelo banco."]
        )
        
    return AgentRuntimeConfig(
        agent_id=agent_id,
        agent_name="Desconhecido",
        is_active=False,
        source="none",
        warnings=[f"Agente '{agent_id}' não localizado."]
    )

def _resolve_from_db(db: Session, agent: db_models.Agent) -> AgentRuntimeConfig:
    """Helper para montar o config resumido a partir do registro do banco."""
    
    config = AgentRuntimeConfig(
        agent_id=agent.id,
        agent_name=agent.name,
        is_active=agent.is_active,
        source="platform_db",
        permissions=json.loads(agent.permissions_json) if agent.permissions_json else {},
        guards=json.loads(agent.guards_json) if agent.guards_json else {},
        behavior=json.loads(agent.behavior_json) if agent.behavior_json else {},
        icon=agent.icon or "🤖"
    )

    # LLM Binding
    llm_binding = db.query(db_models.AgentLLMBinding).filter(
        db_models.AgentLLMBinding.agent_id == agent.id,
        db_models.AgentLLMBinding.is_primary == True,
        db_models.AgentLLMBinding.is_active == True
    ).first()
    
    if llm_binding:
        config.llm_provider_id = llm_binding.provider_id
        config.llm_provider_name = llm_binding.provider.name
        config.llm_model_id = llm_binding.model_id
        config.llm_model_identifier = llm_binding.model.model_identifier
        config.llm_binding_active = True

    # Database Binding (V2 prioritize)
    db_binding = db.query(db_models.AgentDatabaseBindingV2).filter(
        db_models.AgentDatabaseBindingV2.agent_id == agent.id,
        db_models.AgentDatabaseBindingV2.is_primary == True,
        db_models.AgentDatabaseBindingV2.is_active == True
    ).first()
    
    if db_binding:
        conn = db.query(db_models.DatabaseConnection).filter(db_models.DatabaseConnection.id == db_binding.database_connection_id).first()
        if conn:
            config.db_connection_id = conn.id
            config.db_connection_name = conn.name
            config.db_host = conn.host
            config.db_binding_active = True
    else:
        # Fallback Check V1 Bindings if no V2
        v1_binding = db.query(db_models.AgentDatabaseBinding).filter(
            db_models.AgentDatabaseBinding.agent_id == agent.id,
            db_models.AgentDatabaseBinding.is_active == True
        ).first()
        if v1_binding:
            config.db_connection_name = v1_binding.database_name
            config.db_host = v1_binding.host
            config.db_binding_active = True

    return config

def bootstrap_governance_from_yaml(db: Session) -> Dict[str, Any]:
    """
    Importa agentes do YAML para o banco, incluindo prompts, skills e bindings iniciais.
    Busca na pasta de backup legada pois o 'agent_registry' agora opera via DB.
    """
    from pathlib import Path
    import yaml
    from app.schemas.agent import AgentConfig
    
    legacy_dir = Path("config/agents_legacy_backup")
    yaml_agents = []
    
    if legacy_dir.exists():
        for f in legacy_dir.glob("*.yaml"):
            try:
                with open(f, "r", encoding="utf-8") as stream:
                    data = yaml.safe_load(stream)
                    if data:
                        y = AgentConfig.model_validate(data)
                        yaml_agents.append(y)
            except Exception as e:
                logger.error(f"Erro ao carregar YAML legado '{f.name}': {e}")
    
    imported = 0
    skipped = 0
    bindings_created = 0
    
    for y in yaml_agents:

        exists = db.query(db_models.Agent).filter(db_models.Agent.id == y.id).first()
        
        if not exists:
            icon_map = {
                "principal": "🤖",
                "mysql-specialist": "🛠️",
                "mockdata": "📊"
            }
            new_agent = db_models.Agent(
                id=y.id,
                name=y.name,
                description=y.description,
                agent_type=y.type,
                icon=icon_map.get(y.type, "🤖"),
                is_active=True,
                source="yaml_legacy",
                permissions_json=json.dumps(y.permissions.model_dump()) if y.permissions else "{}",
                guards_json=json.dumps(y.guards_json.model_dump()) if hasattr(y, 'guards_json') and y.guards_json else json.dumps(y.guards.model_dump()) if hasattr(y, 'guards') and y.guards else "{}",
                behavior_json=json.dumps(y.behavior.model_dump()) if y.behavior else "{}",
                prompt_file=y.prompt_file,
                skills_json=json.dumps(y.skills) if y.skills else "[]"
            )

            db.add(new_agent)
            imported += 1
            agent_id = y.id
        else:
            skipped += 1
            agent_id = exists.id

        # Verifica e cria amarrações de Database (V1) se necessário
        has_db_binding = db.query(db_models.AgentDatabaseBinding).filter(db_models.AgentDatabaseBinding.agent_id == agent_id).first()
        if not has_db_binding and y.database:
            db_binding = db_models.AgentDatabaseBinding(
                agent_id=agent_id,
                host=y.database.host,
                port=y.database.port,
                database_name=y.database.name,
                username=y.database.user,
                password=y.database.password,
                is_active=True,
                is_default=True
            )
            db.add(db_binding)
            bindings_created += 1

        # Verifica e cria amarrações de LLM (ESSENCIAL para listagem correta)
        has_llm_binding = db.query(db_models.AgentLLMBinding).filter(db_models.AgentLLMBinding.agent_id == agent_id).first()
        if not has_llm_binding:
            model_identifier = y.model or "llama3"
            llm_model = db.query(db_models.LLMModel).filter(db_models.LLMModel.model_identifier == model_identifier).first()
            if llm_model:
                llm_binding = db_models.AgentLLMBinding(
                    agent_id=agent_id,
                    provider_id=llm_model.provider_id,
                    model_id=llm_model.id,
                    is_primary=True,
                    is_active=True
                )
                db.add(llm_binding)
                logger.info(f"Vínculo de LLM criado para '{agent_id}' com modelo '{model_identifier}'")

        
    db.commit()
    logger.info(f"Bootstrap: {imported} agentes, {bindings_created} bindings criados.")
    return {"imported": imported, "skipped": skipped, "bindings_created": bindings_created}
