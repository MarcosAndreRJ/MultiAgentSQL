"""
Base Agent: classe base com comportamento comum a todos os agentes.
"""
from abc import ABC, abstractmethod
from typing import Optional

from app.core.logger import get_logger
from app.schemas.agent import AgentConfig
from app.schemas.chat import Session, LLMPlan, ChatResponse
from sqlalchemy.orm import Session as DBSession

logger = get_logger("base_agent")


class BaseAgent(ABC):
    """
    Classe base para todos os agentes do sistema.
    
    Define:
    - Interface padrão de processamento
    - Validações comuns
    - Logging
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.logger = get_logger(f"agent.{config.id}")

    @property
    def id(self) -> str:
        return self.config.id

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def agent_type(self) -> str:
        return self.config.type

    @property
    def model(self) -> str:
        return self.config.model

    @abstractmethod
    async def process(
        self,
        message: str,
        session: Session,
        resolved_tables: Optional[list[str]] = None,
        run_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        db: Optional[DBSession] = None
    ) -> ChatResponse:
        """
        Processa uma mensagem do usuário e retorna a resposta.
        
        Args:
            message: Texto do usuário (já com aliases resolvidos).
            session: Sessão atual com histórico e contexto.
            resolved_tables: Tabelas originadas de resolução de aliases (para contexto do prompt).
            
        Returns:
            ChatResponse formatada.
        """
        pass

    def can_use_db_tools(self) -> bool:
        """Verifica se o agente tem permissão para usar tools de banco."""
        return (
            self.config.permissions.can_execute
            and self.config.database is not None
        )

    def get_summary(self) -> dict:
        """Retorna resumo do agente para logs."""
        return {
            "id": self.config.id,
            "name": self.config.name,
            "type": self.config.type,
            "model": self.config.model,
            "has_database": self.config.database is not None,
        }
