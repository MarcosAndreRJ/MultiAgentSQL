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

logger = get_logger("governance.service")

class AgentRuntimeConfig(BaseModel):
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
    
    warnings: List[str] = []

def resolve_agent_runtime_config(db: Session, agent_id: str) -> AgentRuntimeConfig:
    """
    Resolve a configuração efetiva de runtime para um agente.
    
    Prioridades:
    1. platform_db (agents table + bindings)
    2. fallback: agent_registry (YAML) com log de warning
    """
    # 1. Tentar buscar registro na tabela agents (DB)
    agent_record = db.query(db_models.Agent).filter(db_models.Agent.id == agent_id).first()
    
    if agent_record:
        return _resolve_from_db(db, agent_record)
    
    # 2. Fallback para YAML (Legado)
    yaml_config = agent_registry.get(agent_id)
    if yaml_config:
        logger.warning(f"Agent '{agent_id}' não encontrado no platform_db. Usando fallback YAML (LEGADO).")
        return AgentRuntimeConfig(
            agent_id=yaml_config.id,
            agent_name=yaml_config.name,
            is_active=True, # YAML sempre ativo por design legado
            source="yaml_fallback",
            permissions=yaml_config.permissions.model_dump() if yaml_config.permissions else {},
            guards=yaml_config.guards.model_dump() if yaml_config.guards else {},
            behavior=yaml_config.behavior.model_dump() if yaml_config.behavior else {},
            warnings=["Usando configuração legada (YAML). Recomenda-se migrar para a governança do banco."]
        )
        
    # 3. Não encontrado
    return AgentRuntimeConfig(
        agent_id=agent_id,
        agent_name="Desconhecido",
        is_active=False,
        source="none",
        warnings=[f"Agente '{agent_id}' não localizado no sistema."]
    )

def _resolve_from_db(db: Session, agent: db_models.Agent) -> AgentRuntimeConfig:
    """Helper para montar o config a partir do registro do banco."""
    
    config = AgentRuntimeConfig(
        agent_id=agent.id,
        agent_name=agent.name,
        is_active=agent.is_active,
        source="platform_db",
        permissions=json.loads(agent.permissions_json) if agent.permissions_json else {},
        guards=json.loads(agent.guards_json) if agent.guards_json else {},
        behavior=json.loads(agent.behavior_json) if agent.behavior_json else {}
    )

    # Resolve LLM Binding Primário
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
    else:
        config.warnings.append("Nenhum LLM Binding PRIMÁRIO ativo encontrado no banco.")

    # Resolve Database Binding Primário
    db_binding = db.query(db_models.AgentDatabaseBindingV2).filter(
        db_models.AgentDatabaseBindingV2.agent_id == agent.id,
        db_models.AgentDatabaseBindingV2.is_primary == True,
        db_models.AgentDatabaseBindingV2.is_active == True
    ).first()
    
    if db_binding:
        config.db_connection_id = db_binding.database_connection_id
        # A relação V2 no models.py pode precisar ser verificada
        # Assumindo que database_connection_id tem backref ou o modelo é simples
        # Se não houver relacionamento explícito, fazemos o query
        conn = db.query(db_models.DatabaseConnection).filter(db_models.DatabaseConnection.id == db_binding.database_connection_id).first()
        if conn:
            config.db_connection_name = conn.name
            config.db_host = conn.host
            config.db_binding_active = True
    else:
        config.warnings.append("Nenhum Database Binding PRIMÁRIO ativo encontrado no banco.")

    return config

def bootstrap_governance_from_yaml(db: Session) -> Dict[str, Any]:
    """
    Importa agentes do YAML para o banco se eles não existirem.
    Deve ser rodado uma única vez ou sob demanda.
    """
    yaml_agents = agent_registry.get_all()
    imported = 0
    skipped = 0
    
    for y in yaml_agents:
        # Verifica se já existe
        exists = db.query(db_models.Agent).filter(db_models.Agent.id == y.id).first()
        if exists:
            skipped += 1
            continue
            
        # Cria registro do agente
        new_agent = db_models.Agent(
            id=y.id,
            name=y.name,
            description=f"Importado do YAML ({y.type})",
            agent_type=y.type,
            is_active=True,
            source="yaml_legacy",
            permissions_json=json.dumps(y.permissions.model_dump()) if y.permissions else "{}",
            guards_json=json.dumps(y.guards.model_dump()) if y.guards else "{}",
            behavior_json=json.dumps(y.behavior.model_dump()) if y.behavior else "{}"
        )
        db.add(new_agent)
        imported += 1
        
    db.commit()
    logger.info(f"Bootstrap Governance: {imported} agentes importados, {skipped} pulados (já existiam).")
    return {"imported": imported, "skipped": skipped}
