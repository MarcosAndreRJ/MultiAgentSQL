"""
Schemas para configuração de agentes.
"""
from typing import Optional, Any
from pydantic import BaseModel, Field, model_validator


class AgentLLMConfig(BaseModel):
    """Configuração de provider LLM por agente. Opcional — sem ela usa Ollama retrocompat."""
    provider: str = "ollama"               # "ollama" | "gemini"
    model: Optional[str] = None            # Sobrescreve o campo model do agente
    base_url: Optional[str] = None         # URL customizada (ex: para cloud/proxy)
    api_key: Optional[str] = None          # Chave de API (opcional)
    fallback_provider: Optional[str] = None  # Provider secundário em caso de falha
    fallback_model: Optional[str] = None     # Modelo do provider secundário
    timeout_seconds: int = 120


class DatabaseConfig(BaseModel):
    """Configuração de banco de dados para agente especialista."""
    host: str = "localhost"
    port: int = 3306
    name: str
    user: str
    password: str = ""
    connect_timeout: int = 10
    pool_size: int = 3


class AgentPermissions(BaseModel):
    """Permissões do agente."""
    can_read_db: bool = False
    can_write_db: bool = False
    can_ddl: bool = False
    can_execute: bool = False
    protected_tables: list[str] = Field(default_factory=list)


class AgentGuards(BaseModel):
    """Configuração de guards do agente."""
    require_confirmation_for: list[str] = Field(
        default_factory=lambda: ["DELETE", "DROP", "TRUNCATE", "UPDATE_WITHOUT_WHERE", "ALTER_DESTRUCTIVE"]
    )
    auto_approve: list[str] = Field(
        default_factory=lambda: ["SELECT", "SHOW", "DESCRIBE", "EXPLAIN"]
    )


class AgentBehavior(BaseModel):
    """Configuração de comportamento do agente."""
    max_loop_steps: int = 3
    response_style: str = "technical"
    language: str = "pt-BR"
    max_result_rows: int = 500
    introspect_before_ddl: bool = True


class AgentConfig(BaseModel):
    """Configuração completa de um agente (lida do YAML)."""
    id: str
    name: str
    description: str
    type: str  # "principal" | "mysql-specialist"
    model: str
    prompt_file: str
    skills: list[str] = Field(default_factory=list)
    database: Optional[DatabaseConfig] = None
    permissions: AgentPermissions = Field(default_factory=AgentPermissions)
    guards: AgentGuards = Field(default_factory=AgentGuards)
    behavior: AgentBehavior = Field(default_factory=AgentBehavior)
    llm: Optional[AgentLLMConfig] = None  # Configuração multi-provider (opcional)

    @model_validator(mode='before')
    @classmethod
    def migrate_llm_fields(cls, data: Any) -> Any:
        """Move campos de LLM soltos na raiz para dentro do objeto 'llm'."""
        if isinstance(data, dict):
            # Se já tem 'llm', não fazemos nada (prioridade para a seção explícita)
            if data.get("llm") is not None:
                return data

            # Campos alvo de migração
            llm_fields = ["provider", "timeout_seconds", "fallback_provider", "fallback_model", "base_url", "api_key"]
            
            # Se encontrar o campo 'provider' na raiz, assume que o usuário quer configurar LLM aqui
            if any(k in data for k in llm_fields):
                llm_data = {}
                for f in llm_fields:
                    if f in data:
                        llm_data[f] = data.pop(f)
                
                # O 'model' da raiz é o model default se llm['model'] não for definido
                # mas o AgentConfig exige 'model' na raiz, então deixamos lá também.
                llm_data["model"] = data.get("model")
                
                data["llm"] = llm_data
        return data


class AgentSummary(BaseModel):
    """Resumo de agente para listagem na API."""
    id: str
    name: str
    description: str
    type: str
    model: str
    database_name: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    is_online: bool = False


class AgentDetail(AgentSummary):
    """Detalhes completos de agente para a API."""
    prompt_preview: Optional[str] = None
    permissions: AgentPermissions
    guards: AgentGuards
    behavior: AgentBehavior
