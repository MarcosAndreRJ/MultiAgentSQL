"""
Agent Service: operações sobre agentes (listagem, detalhes, status de conexão).
"""
from typing import Optional, List
import uuid
import yaml
import json
from pathlib import Path

from app.core import agent_registry
from app.core.logger import get_logger
from app.core.settings import settings
from app.schemas.agent import AgentSummary, AgentDetail, AgentCreate, AgentUpdate, DatabaseConfig
from app.db.session import SessionLocal
from app.db import models as db_models
from sqlalchemy import text
import time
from app.utils.crypto import encrypt_secret

logger = get_logger("agent_service")


async def create_agent(data: AgentCreate, db_session: Optional[SessionLocal] = None) -> AgentSummary:
    """
    Cria um novo agente:
    1. Gera ID único
    2. Persiste na tabela 'agents' do platform_db
    3. Cria binding de banco operacional (target_db) na tabela 'agent_database_bindings'
    """
    own_session = False
    if db_session is None:
        db_session = SessionLocal()
        own_session = True

    try:
        agent_id = f"agent_{uuid.uuid4().hex[:8]}"
        
        # Escolha de modelo: manual ou assistida
        model_to_use = data.model
        if not model_to_use:
            from app.services.dashboard.models_service import get_best_available_model
            try:
                model_to_use = await get_best_available_model(db_session)
            except Exception:
                model_to_use = "llama3"

        # Configurações padrão para novo agente
        import json
        permissions = {
            "can_read_db": True,
            "can_write_db": True,
            "can_ddl": False,
            "can_execute": True,
            "protected_tables": []
        }
        guards = {
            "require_confirmation_for": ["DELETE", "DROP", "TRUNCATE"],
            "auto_approve": ["SELECT", "SHOW", "DESCRIBE"]
        }
        behavior = {
            "max_loop_steps": 3,
            "response_style": "technical",
            "language": "pt-BR",
            "max_result_rows": 500,
            "introspect_before_ddl": True
        }

        # 1. Persistir o Agente (Governança)
        new_agent = db_models.Agent(
            id=agent_id,
            name=data.name,
            description=data.description,
            agent_type=data.type or "mysql-specialist",
            is_active=True,
            source="dashboard",
            prompt_file=data.prompt_file or "base.txt",
            skills_json="[]",
            icon=data.icon or "🤖",
            permissions_json=json.dumps(permissions),
            guards_json=json.dumps(guards),
            behavior_json=json.dumps(behavior)
        )
        db_session.add(new_agent)

        # 2. Criar Binding de Banco (Operacional) V2
        if data.database:
            enc_pass = encrypt_secret(data.database.password or "")
            db_conn = db_models.DatabaseConnection(
                name=f"Conn_{agent_id}",
                db_type="mysql",
                host=data.database.host,
                port=data.database.port,
                database_name=data.database.name,
                username=data.database.user,
                password_encrypted=enc_pass,
                is_active=True
            )
            db_session.add(db_conn)
            db_session.flush() # Para pegar o db_conn.id
            
            bind_v2 = db_models.AgentDatabaseBindingV2(
                agent_id=agent_id,
                database_connection_id=db_conn.id,
                is_default=True,
                is_primary=True,
                access_mode="readwrite",
                is_active=True
            )
            db_session.add(bind_v2)
            
        # 3. Criar Binding de LLM (Governança)
        # Tenta vincular ao modelo escolhido
        from app.db import models as models
        llm_model = db_session.query(models.LLMModel).filter(models.LLMModel.model_identifier == model_to_use).first()
        if llm_model:
            llm_binding = models.AgentLLMBinding(
                agent_id=agent_id,
                provider_id=llm_model.provider_id,
                model_id=llm_model.id,
                is_primary=True,
                is_active=True
            )
            db_session.add(llm_binding)

        db_session.commit()
        logger.info(f"Agente {agent_id} criado com sucesso no banco de dados.")

        return AgentSummary(
            id=agent_id,
            name=data.name,
            description=data.description,
            type=new_agent.agent_type,
            model=model_to_use,
            icon=new_agent.icon,
            database_name=data.database.name if data.database else None,
            skills=[],
            is_online=True
        )
    except Exception as e:
        db_session.rollback()
        logger.error(f"Erro ao criar agente no banco: {e}")
        raise e
    finally:
        if own_session:
            db_session.close()


async def list_agents() -> list[AgentSummary]:
    """Lista todos os agentes ativos no banco de dados."""
    try:
        db = SessionLocal()
        try:
            agents = db.query(db_models.Agent).filter(db_models.Agent.is_active == True).all()
            summaries = []
            
            for ag in agents:
                # Resolve o modelo vinculado
                from app.services.platform import agent_governance_service
                runtime = agent_governance_service.resolve_agent_runtime_config(db, ag.id)
                
                summary = AgentSummary(
                    id=ag.id,
                    name=ag.name,
                    description=ag.description or "",
                    type=ag.agent_type,
                    model=runtime.llm_model_identifier or "unknown",
                    icon=ag.icon or "🤖",
                    database_name=runtime.db_connection_name if runtime.db_connection_name else None,
                    skills=json.loads(ag.skills_json) if ag.skills_json else [],
                    is_online=True,
                )
                summaries.append(summary)
            
            return summaries
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Falha de conexão com o banco de dados de plataforma: {e}")
        # Retornamos lista vazia ou levantamos erro específico tratado pelo middleware
        raise ConnectionError(f"Erro ao conectar ao banco de governança (192.168.0.5): {str(e)}")


async def get_agent_detail(agent_id: str) -> Optional[AgentDetail]:
    """Retorna detalhes completos de um agente consultando o banco de dados."""
    db = SessionLocal()
    try:
        from app.services.platform import agent_governance_service
        config = agent_governance_service.resolve_full_agent(db, agent_id)
        if not config:
            return None

        from app.agents.prompt_builder import load_base_prompt
        try:
            full_prompt = load_base_prompt(config)
            prompt_preview = full_prompt[:500] + "..." if len(full_prompt) > 500 else full_prompt
        except Exception:
            prompt_preview = None

        return AgentDetail(
            id=config.id,
            name=config.name,
            description=config.description,
            type=config.type,
            model=config.model,
            icon=config.icon,
            database_name=config.database.name if config.database else None,
            database=config.database,
            skills=config.skills,
            is_online=True,
            prompt_preview=prompt_preview,
            permissions=config.permissions,
            guards=config.guards,
            behavior=config.behavior,
        )
    finally:
        db.close()


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


async def update_agent(agent_id: str, data: AgentUpdate, db_session: Optional[SessionLocal] = None) -> List[AgentSummary]:
    """
    Atualiza um agente existente:
    1. Atualiza metadados na tabela 'agents'
    2. Atualiza binding de banco (V1)
    3. Atualiza binding de LLM se o model mudar
    """
    from app.schemas.agent import AgentSummary
    own_session = False
    if db_session is None:
        db_session = SessionLocal()
        own_session = True

    try:
        agent = db_session.query(db_models.Agent).filter(db_models.Agent.id == agent_id).first()
        if not agent:
            raise ValueError(f"Agente '{agent_id}' não encontrado")

        if data.name is not None: agent.name = data.name
        if data.description is not None: agent.description = data.description
        if data.type is not None: agent.agent_type = data.type
        if data.icon is not None: agent.icon = data.icon

        # Atualizar Banco (Target DB) utilizando V2 nativo
        if data.database:
            # Tenta encontrar o binding primário V2
            bind_v2 = db_session.query(db_models.AgentDatabaseBindingV2).filter(
                db_models.AgentDatabaseBindingV2.agent_id == agent_id,
                db_models.AgentDatabaseBindingV2.is_primary == True,
                db_models.AgentDatabaseBindingV2.is_active == True
            ).first()

            enc_pass = encrypt_secret(data.database.password or "")

            if bind_v2:
                # Atualizar a conexão existente
                db_conn = db_session.query(db_models.DatabaseConnection).filter(
                    db_models.DatabaseConnection.id == bind_v2.database_connection_id
                ).first()
                if db_conn:
                    db_conn.host = data.database.host
                    db_conn.port = data.database.port
                    db_conn.database_name = data.database.name
                    db_conn.username = data.database.user
                    if data.database.password:
                        db_conn.password_encrypted = enc_pass
            else:
                # Não há binding V2, criar uma conexão nova + binding
                db_conn = db_models.DatabaseConnection(
                    name=f"Conn_{agent_id}",
                    db_type="mysql",
                    host=data.database.host,
                    port=data.database.port,
                    database_name=data.database.name,
                    username=data.database.user,
                    password_encrypted=enc_pass,
                    is_active=True
                )
                db_session.add(db_conn)
                db_session.flush()

                new_bind = db_models.AgentDatabaseBindingV2(
                    agent_id=agent_id,
                    database_connection_id=db_conn.id,
                    is_default=True,
                    is_primary=True,
                    access_mode="readwrite",
                    is_active=True
                )
                db_session.add(new_bind)

        # Atualizar LLM
        model_to_use = data.model
        if model_to_use:
            # Desativa bindings anteriores e cria/ativa o novo
            db_session.query(db_models.AgentLLMBinding).filter(db_models.AgentLLMBinding.agent_id == agent_id).update({"is_primary": False})
            
            llm_model = db_session.query(db_models.LLMModel).filter(db_models.LLMModel.model_identifier == model_to_use).first()
            if llm_model:
                binding = db_session.query(db_models.AgentLLMBinding).filter(
                    db_models.AgentLLMBinding.agent_id == agent_id,
                    db_models.AgentLLMBinding.model_id == llm_model.id
                ).first()
                
                if binding:
                    binding.is_primary = True
                    binding.is_active = True
                else:
                    new_binding = db_models.AgentLLMBinding(
                        agent_id=agent_id,
                        provider_id=llm_model.provider_id,
                        model_id=llm_model.id,
                        is_primary=True,
                        is_active=True
                    )
                    db_session.add(new_binding)

        # Atualização de Configurações Avançadas
        if data.permissions is not None:
            agent.permissions_json = data.permissions.model_dump_json()
        if data.guards is not None:
            agent.guards_json = data.guards.model_dump_json()
        if data.behavior is not None:
            agent.behavior_json = data.behavior.model_dump_json()

        db_session.commit()
        # Retorna a lista atualizada
        return await list_agents()
    except Exception as e:
        db_session.rollback()
        logger.error(f"Erro ao atualizar agente '{agent_id}': {e}")
        raise e
    finally:
        if own_session:
            db_session.close()