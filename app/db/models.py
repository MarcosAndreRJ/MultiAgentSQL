"""
Modelos ORM (Tabelas) do Banco de Dados MySQL.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, UniqueConstraint, Float
from sqlalchemy.orm import relationship

from app.db.session import Base

class LLMProvider(Base):
    """Tabela de provedores de LLM."""
    __tablename__ = "llm_providers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    provider_type = Column(String(20), nullable=False)  # "ollama", "gemini", "openai"
    base_url = Column(String(255), nullable=True)
    api_key_masked = Column(String(100), nullable=True)
    api_key = Column(Text, nullable=True) # Campo para a chave real (persistência local)
    is_active = Column(Boolean, default=True)
    source = Column(String(20), default="live")        # "bootstrap", "live", "manual"
    
    last_status = Column(String(20), nullable=True)     # "ok", "error", "unknown"
    last_test_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamento com modelos
    models = relationship("LLMModel", back_populates="provider", cascade="all, delete-orphan")

class LLMModel(Base):
    """Tabela de modelos disponíveis por provedor."""
    __tablename__ = "llm_models"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("llm_providers.id"), nullable=False)
    model_identifier = Column(String(100), nullable=False, index=True) # Nome técnico (ex: llama3)
    display_name = Column(String(100), nullable=False)                 # Nome amigável (ex: Llama 3)
    
    supports_tools = Column(Boolean, default=False)
    supports_json = Column(Boolean, default=False)
    supports_streaming = Column(Boolean, default=True)
    context_window = Column(Integer, nullable=True)                    # Janela de contexto em tokens
    
    is_available = Column(Boolean, default=True)                       # Disponibilidade técnica (detectada no sync)
    is_active = Column(Boolean, default=True)                          # Ativo para uso (governança)
    
    source = Column(String(20), default="sync")        # "sync", "manual", "bootstrap"

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamento com o provider
    provider = relationship("LLMProvider", back_populates="models")




class DatabaseConnection(Base):
    """Entidade que representa uma conexão a um banco operacional (target DB).

    Essa tabela é a forma normalizada de persistir credenciais e metadados de
    conexões. Não substitui imediatamente a tabela legada `agent_database_bindings`:
    a etapa atual cria a estrutura para uso futuro sem quebrar o runtime.
    """

    __tablename__ = "database_connections"
    __table_args__ = ()

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    db_type = Column(String(30), nullable=False, default="mysql")
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False, default=3306)
    database_name = Column(String(255), nullable=False)
    username = Column(String(255), nullable=False)
    password_encrypted = Column(Text, nullable=False)
    extra_config_json = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentDatabaseBindingV2(Base):
    """Vínculo Agent -> DatabaseConnection (nova versão normalizada).

    Mantemos essa tabela separada da tabela legada para permitir migração
    incremental sem alterar o comportamento atual do runtime.
    """

    __tablename__ = "agent_database_bindings_v2"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String(100), nullable=False, index=True)
    database_connection_id = Column(Integer, ForeignKey("database_connections.id"), nullable=False)
    is_default = Column(Boolean, default=False)
    is_primary = Column(Boolean, default=False) # Define qual é o principal para governança
    access_mode = Column(String(20), default="readonly")  # readonly | readwrite
    schema_scope = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Agent(Base):
    """Tabela de agentes na plataforma (governança centralizada).
    Substitui a necessidade de YAMLs como fonte da verdade.
    """
    __tablename__ = "agents"

    id = Column(String(100), primary_key=True, index=True) # ID único (ex: agent_sql)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    agent_type = Column(String(50), nullable=False, default="database")
    icon = Column(String(20), nullable=True, default="🤖")

    
    is_active = Column(Boolean, default=True, nullable=False)
    source = Column(String(20), default="yaml_legacy") # yaml_legacy, dashboard, api
    
    # Flags administrativas (serializadas como JSON)
    permissions_json = Column(Text, nullable=True) # Antes em YAML: permissions
    guards_json = Column(Text, nullable=True)      # Antes em YAML: guards
    behavior_json = Column(Text, nullable=True)    # Antes em YAML: behavior
    
    # Configurações de conteúdo (referências)
    prompt_file = Column(String(100), nullable=True)
    skills_json = Column(Text, nullable=True) # Lista de IDs de skills em formato JSON

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentLLMBinding(Base):
    """Vincula um agente ao provider/modelo LLM no platform_db."""

    __tablename__ = "agent_llm_bindings"
    __table_args__ = (
        UniqueConstraint("agent_id", "provider_id", "model_id", name="uq_agent_provider_model"),
    )

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String(100), nullable=False, index=True)
    provider_id = Column(Integer, ForeignKey("llm_providers.id"), nullable=False, index=True)
    model_id = Column(Integer, ForeignKey("llm_models.id"), nullable=False, index=True)
    is_default = Column(Boolean, default=False)
    is_primary = Column(Boolean, default=False) # Define qual é o principal para governança
    fallback_order = Column(Integer, nullable=False, default=0)
    supports_json_required = Column(Boolean, default=False)
    supports_tools_required = Column(Boolean, default=False)
    # New governance fields (Etapa 6)
    fallback_provider_id = Column(Integer, ForeignKey("llm_providers.id"), nullable=True, index=True)
    fallback_model_id = Column(Integer, ForeignKey("llm_models.id"), nullable=True, index=True)
    require_streaming = Column(Boolean, default=False)
    min_context_window = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    provider = relationship("LLMProvider", foreign_keys=[provider_id])
    model = relationship("LLMModel", foreign_keys=[model_id])
    # Optional relationships for fallback (no cascade)
    fallback_provider = relationship("LLMProvider", foreign_keys=[fallback_provider_id])
    fallback_model = relationship("LLMModel", foreign_keys=[fallback_model_id])


class AgentExecutionLog(Base):
    """Logs de execução SQL por agente (observabilidade operacional)."""

    __tablename__ = "agent_execution_logs"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String(64), nullable=False, index=True)
    agent_id = Column(String(100), nullable=False, index=True)
    provider_id = Column(Integer, ForeignKey("llm_providers.id"), nullable=True, index=True)
    model_id = Column(Integer, ForeignKey("llm_models.id"), nullable=True, index=True)
    database_connection_id = Column(Integer, ForeignKey("database_connections.id"), nullable=True, index=True)
    query = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, index=True)  # success | error
    execution_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    result_summary_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class ProviderExecutionLog(Base):
    """Logs de chamadas de provider para rastreabilidade e latência."""

    __tablename__ = "provider_execution_logs"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String(64), nullable=False, index=True)
    provider_id = Column(Integer, ForeignKey("llm_providers.id"), nullable=True, index=True)
    model_id = Column(Integer, ForeignKey("llm_models.id"), nullable=True, index=True)
    operation = Column(String(50), nullable=False)  # test_connection | sync_models | completion ...
    status = Column(String(20), nullable=False, index=True)  # success | error
    latency_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class HealthCheckLog(Base):
    """Log histórico de saúde e observabilidade operacional."""

    __tablename__ = "health_check_logs"

    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String(30), nullable=False, index=True)      # platform | provider | target_db
    entity_id = Column(String(100), nullable=True, index=True)   # ID do provider ou banco
    entity_name = Column(String(100), nullable=True)             # Nome amigável
    status = Column(String(20), nullable=False)                  # healthy | degraded | offline
    latency_ms = Column(Integer, nullable=True)                  # latência em ms
    message = Column(Text, nullable=True)                        # Erro ou mensagem amigável
    details_json = Column(Text, nullable=True)                   # Detalhes técnicos (JSON string)
    execution_id = Column(String(64), nullable=True, index=True) # Correlação opcional entre domínios
    checked_at = Column(DateTime, default=datetime.utcnow, index=True)


class SentinelSnapshot(Base):
    """Snapshot periódico do estado de um provider (Sentinel)."""

    __tablename__ = "sentinel_provider_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("llm_providers.id"), index=True)
    checked_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Métricas de Catálogo
    models_total = Column(Integer, default=0)
    models_new = Column(Integer, default=0)
    models_updated = Column(Integer, default=0)
    models_unavailable = Column(Integer, default=0)
    
    # Métricas de Carteira/Saldo
    credits_available = Column(Float, nullable=True)
    credits_currency = Column(String(10), nullable=True) # USD, BRL, tokens...
    
    # Status Operacional
    status = Column(String(20), nullable=False) # healthy | degraded | critical
    message = Column(Text, nullable=True)
    
    provider = relationship("LLMProvider", foreign_keys=[provider_id])


class SentinelConsistencyScore(Base):
    """Score de consistência/estabilidade histórica (Sentinel)."""

    __tablename__ = "sentinel_consistency_scores"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("llm_providers.id"), index=True)
    model_id = Column(Integer, ForeignKey("llm_models.id"), nullable=True, index=True)
    
    score = Column(Integer, default=100) # 0 a 100
    status = Column(String(20), default="stable") # stable | warning | critical
    reason = Column(Text, nullable=True)
    
    calculated_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    provider = relationship("LLMProvider", foreign_keys=[provider_id])
    model = relationship("LLMModel", foreign_keys=[model_id])
