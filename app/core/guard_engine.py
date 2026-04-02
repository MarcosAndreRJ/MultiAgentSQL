"""
Guard Engine: avalia risco e decide se SQL pode ser executado diretamente
ou se precisa de confirmação via pending action.

Responsabilidade: DECISÃO de execução baseada em risco.
Não executa SQL — apenas decide.
"""
from app.core.sql_classifier import classify_sql
from app.core.logger import get_logger
from app.schemas.agent import AgentConfig, AgentGuards
from app.schemas.guard import GuardDecision, SQLClassification

logger = get_logger("guard_engine")


def evaluate(sql: str, agent: AgentConfig) -> GuardDecision:
    """
    Avalia o SQL contra as políticas do agente e decide:
    - allowed: se pode ser processado
    - requires_confirmation: se precisa de pending action
    
    Args:
        sql: O SQL a ser avaliado.
        agent: Configuração do agente com políticas de guard.
        
    Returns:
        GuardDecision com a decisão e contexto.
    """
    classification = classify_sql(sql)
    guards = agent.guards
    permissions = agent.permissions

    # Verificar permissões básicas do agente
    if not permissions.can_execute:
        return GuardDecision(
            allowed=False,
            requires_confirmation=False,
            risk_level=classification.risk_level,
            reason="Agente não tem permissão para executar SQL",
            classification=classification,
        )

    # Agente sem permissão de escrita/DDL tentando fazer isso
    if classification.sql_type in ("INSERT", "UPDATE", "DELETE") and not permissions.can_write_db:
        return GuardDecision(
            allowed=False,
            requires_confirmation=False,
            risk_level=classification.risk_level,
            reason="Agente não tem permissão para operações de escrita",
            classification=classification,
        )

    if classification.sql_type in ("CREATE", "ALTER", "DROP", "TRUNCATE") and not permissions.can_ddl:
        return GuardDecision(
            allowed=False,
            requires_confirmation=False,
            risk_level=classification.risk_level,
            reason="Agente não tem permissão para operações DDL",
            classification=classification,
        )

    # Verificar tabelas protegidas
    if permissions.protected_tables:
        for obj in classification.affected_objects:
            if obj.lower() in [t.lower() for t in permissions.protected_tables]:
                return GuardDecision(
                    allowed=False,
                    requires_confirmation=False,
                    risk_level="high",
                    reason=f"Tabela protegida: {obj}",
                    classification=classification,
                )

    # Decidir se precisa de confirmação baseado nas políticas do agente
    requires_confirmation = _needs_confirmation(classification, guards)

    if requires_confirmation:
        logger.info(
            f"Guard: confirmação necessária | tipo={classification.sql_type} | risco={classification.risk_level}"
        )
        return GuardDecision(
            allowed=True,
            requires_confirmation=True,
            risk_level=classification.risk_level,
            reason=_build_confirmation_reason(classification),
            classification=classification,
        )

    logger.debug(
        f"Guard: aprovado direto | tipo={classification.sql_type} | risco={classification.risk_level}"
    )
    return GuardDecision(
        allowed=True,
        requires_confirmation=False,
        risk_level=classification.risk_level,
        reason="Aprovado automaticamente",
        classification=classification,
    )


def _needs_confirmation(classification: SQLClassification, guards: AgentGuards) -> bool:
    """
    Determina se a operação precisa de confirmação baseada nas políticas.
    """
    sql_type = classification.sql_type
    require_list = [r.upper() for r in guards.require_confirmation_for]
    auto_list = [a.upper() for a in guards.auto_approve]

    # AUTO-APPROVE tem precedência para tipos de leitura
    if sql_type in auto_list:
        return False

    # Verificar mapeamentos especiais
    # UPDATE sem WHERE
    if sql_type == "UPDATE" and not classification.has_where:
        if "UPDATE_WITHOUT_WHERE" in require_list:
            return True

    # DELETE sempre exige se configurado
    if sql_type == "DELETE" and "DELETE" in require_list:
        return True

    # DROP sempre exige se configurado
    if sql_type == "DROP" and "DROP" in require_list:
        return True

    # TRUNCATE
    if sql_type == "TRUNCATE" and "TRUNCATE" in require_list:
        return True

    # ALTER destrutivo
    if sql_type == "ALTER" and classification.is_destructive and "ALTER_DESTRUCTIVE" in require_list:
        return True

    # Risco high sempre exige confirmação
    if classification.risk_level == "high":
        return True

    return False


def _build_confirmation_reason(classification: SQLClassification) -> str:
    """Constrói uma mensagem explicando por que a confirmação é necessária."""
    parts = [f"Operação {classification.sql_type} com risco {classification.risk_level.upper()} requer confirmação."]
    if classification.warnings:
        parts.extend(classification.warnings)
    if classification.affected_objects:
        parts.append(f"Objetos afetados: {', '.join(classification.affected_objects)}")
    return " | ".join(parts)
