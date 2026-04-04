"""
Principal Agent: agente generalista sem acesso a banco de dados.
Serve para explicações técnicas, revisão de SQL e orientação conceitual.
"""
from typing import Optional

from app.agents.base_agent import BaseAgent
from app.agents.prompt_builder import build_full_prompt
from app.core import session_store
from app.core.logger import get_logger
from app.schemas.agent import AgentConfig
from app.schemas.chat import Session, ChatResponse
from app.services.llm.factory import get_provider
from app.services.llm.base import LLMProviderError
from sqlalchemy.orm import Session as DBSession

logger = get_logger("principal_agent")


class PrincipalAgent(BaseAgent):
    """
    Agente generalista — não executa operações reais em banco.
    Responde em linguagem natural após chamar o LLM diretamente.
    """

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        if config.type != "principal":
            raise ValueError(f"PrincipalAgent requer type='principal', recebeu '{config.type}'")

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
        Processa mensagem sem tools de banco.
        
        Fluxo:
        1. Constrói prompt completo
        2. Chama Ollama
        3. Retorna resposta informativa
        """
        self.logger.info(f"Processando | sessão={session.session_id} | msg_len={len(message)}")

        # Registrar mensagem do usuário na sessão
        session_store.add_message(session.session_id, "user", message)

        # Montar prompt final
        full_prompt = build_full_prompt(
            agent=self.config,
            session=session,
            user_message=message,
            resolved_tables=resolved_tables,
        )

        # Chamar LLM via Factory
        llm = get_provider(self.config)
        try:
            response_text = await llm.chat_async(
                prompt=full_prompt,
                temperature=0.3,
                execution_id=execution_id,
                db=db,
            )
        except LLMProviderError as e:
            error_msg = self._format_error(str(e))
            session_store.add_message(session.session_id, "assistant", error_msg)
            return ChatResponse(
                session_id=session.session_id,
                agent_id=self.id,
                response=error_msg,
                status="error",
            )

        # Registrar resposta no histórico
        session_store.add_message(session.session_id, "assistant", response_text)

        return ChatResponse(
            session_id=session.session_id,
            agent_id=self.id,
            response=response_text,
            status="completed",
        )

    def _format_error(self, error: str) -> str:
        return (
            f"[ERRO]\n{error}\n\n"
            f"[PRÓXIMO PASSO]\nVerifique se o Ollama está rodando com o modelo '{self.model}'."
        )
