"""
Database Agent: agente especialista vinculado a um banco MySQL.
Implementa o agent loop completo: plan → tools → guard → execute → respond.
"""
from typing import Optional

from app.agents.base_agent import BaseAgent
from app.agents.prompt_builder import build_full_prompt
from app.core import session_store, guard_engine, pending_actions as pa_store
from app.core.logger import get_logger
from app.core.sql_classifier import classify_sql
from app.schemas.agent import AgentConfig
from app.schemas.chat import Session, LLMPlan, ChatResponse
from app.schemas.execution import DBExecuteRequest
from app.services import fastpath_service, fastpath_v2_service, ollama_client, progress_service
from app.services.llm.factory import get_provider
from app.services.llm.base import LLMProviderError
from app.tools import db_execute, db_introspection, db_mockdata
from app.tools.db_mockdata import generate_and_insert
from app.utils.text_formatter import format_rows

logger = get_logger("database_agent")

# Máximo de iterações no loop interno para evitar loops infinitos
MAX_LOOP_STEPS = 5


class DatabaseAgent(BaseAgent):
    """
    Agente especialista MySQL.
    Implementa o agent loop completo com tools, guard e pending actions.
    """

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        if not config.database:
            raise ValueError(f"DatabaseAgent '{config.id}' requer configuração de database")

    async def process(
        self,
        message: str,
        session: Session,
        resolved_tables: Optional[list[str]] = None,
        run_id: Optional[str] = None
    ) -> ChatResponse:
        """
        Agent loop principal:
        1. Construir contexto
        2. Gerar plano (LLM)
        3. Executar tools
        4. Avaliar guard
        5. Criar pending action (se necessário) ou executar
        6. Responder ao usuário
        """
        import time
        _t0 = time.monotonic()
        self.logger.info(f"[AGENT] Iniciando | agente={self.id} | modelo={self.model} | msg='{message[:80]}'")

        # Registrar mensagem do usuário
        session_store.add_message(session.session_id, "user", message)

        # Fast-Path V2 (Semântico, guiado pelo digest) — executa antes do V1 e do LLM
        if run_id: await progress_service.emit_step(session.session_id, run_id, "semantic_search")
        v2_result = await fastpath_v2_service.execute(self.config, message, session)
        if v2_result:
            if run_id: await progress_service.emit_step(session.session_id, run_id, "semantic_search", status="completed")
            self.logger.info(
                f"[FAST_PATH_V2] Concluído em {(time.monotonic()-_t0)*1000:.0f}ms "
                f"| intent={v2_result.intent} | tabelas={v2_result.table_name}"
            )
            return ChatResponse(
                session_id=session.session_id,
                agent_id=self.id,
                response=v2_result.response,
                sql_executed=v2_result.sql,
                status="completed",
                model=self.model,
                execution_source="fast_path",
                used_llm=False,
                latency_ms=(time.monotonic() - _t0) * 1000,
                metadata=v2_result.metadata
            )

        # Roteamento Fast-Path V1 (Zero LLM) — tenta resolver sem LLM
        if run_id: await progress_service.emit_step(session.session_id, run_id, "fast_path_check")
        fast_result = await fastpath_service.execute_fast_path(self.config, message, session)
        if fast_result:
            if run_id: await progress_service.emit_step(session.session_id, run_id, "fast_path_check", status="completed")
            self.logger.info(
                f"[FAST_PATH] Concluído em {(time.monotonic()-_t0)*1000:.0f}ms "
                f"| intent={fast_result.intent} | tabela={fast_result.table_name}"
            )
            return ChatResponse(
                session_id=session.session_id,
                agent_id=self.id,
                response=fast_result.response,
                sql_executed=fast_result.sql,
                status="completed",
                model=self.model,
                execution_source=fast_result.execution_source,
                used_llm=False,
                latency_ms=(time.monotonic() - _t0) * 1000,
                metadata=fast_result.metadata
            )

        # Roteamento Semântico V3 (Memória de queries pregressas parametrizadas)
        from app.services.semantic.pattern_matcher import match_and_execute
        semantic_result = await match_and_execute(self.config, message, session)
        if semantic_result:
            self.logger.info(
                f"[SEMANTIC_V3] Concluído em {(time.monotonic()-_t0)*1000:.0f}ms "
                f"| intent={semantic_result.intent} | tabelas={semantic_result.table_name}"
            )
            return ChatResponse(
                session_id=session.session_id,
                agent_id=self.id,
                response=semantic_result.response,
                sql_executed=semantic_result.sql,
                status="completed",
                model=self.model,
                execution_source=semantic_result.execution_source,
                used_llm=False,
                latency_ms=(time.monotonic() - _t0) * 1000,
                metadata=semantic_result.metadata
            )

        self.logger.info("[FAST_PATH_MISS] Nenhum intent rápido ou semântico detectado → iniciando LLM.")

        max_steps = self.config.behavior.max_loop_steps or 3
        
        for step in range(max_steps):
            self.logger.info(f"[AGENT LOOP] Step {step + 1}/{max_steps}")
            
            # Em passos iterativos, incluir dados reais das tools na mensagem de feedback
            current_msg = message
            # Em step > 0 não repassamos resolved_tables (contexto já foi injetado no step 0)
            step_resolved = resolved_tables if step == 0 else None
            if step > 0:
                tool_data = _summarize_last_tool_results(session)
                current_msg = (
                    f"As ferramentas foram executadas. Dados reais obtidos:\n\n{tool_data}\n\n"
                    "Com base nos dados ACIMA (não no histórico), responda ao usuário:\n"
                    "- Se os dados respondem a pergunta: retorne needs_tools=false e transcreva os dados "
                    "reais no campo 'explanation' de forma legível (o usuário SÓ vê a explanation).\n"
                    "- Se precisar de mais dados: use novas ferramentas com needs_tools=true."
                )

            # Construir prompt completo
            full_prompt = build_full_prompt(
                agent=self.config,
                session=session,
                user_message=current_msg,
                resolved_tables=step_resolved,
            )
            self.logger.debug(f"[AGENT] Prompt total: {len(full_prompt)} chars")

            # Gerar plano estruturado do LLM
            _llm_provider = get_provider(self.config)
            try:
                plan = await _llm_provider.get_plan_async(
                    system_prompt=full_prompt,
                    user_message=current_msg,
                )
            except LLMProviderError as e:
                self.logger.error(f"[AGENT] LLMProviderError: {e}")
                return self._error_response(session, str(e))

            # Coletar metadados do provider (suporte a fallback)
            from app.services.llm.factory import FallbackProvider
            _provider_used = getattr(_llm_provider, 'last_used_provider', _llm_provider.provider_name) or _llm_provider.provider_name
            _model_used = _llm_provider.model_name
            _fallback_used = getattr(_llm_provider, 'fallback_was_used', False)
            _fallback_from = getattr(_llm_provider, 'fallback_from', None)
            if isinstance(_llm_provider, FallbackProvider) and _fallback_used:
                # O modelo do provider winner é o do fallback
                _model_used = _llm_provider._fallback.model_name
                self.logger.warning(
                    f"[LLM_PROVIDER_FALLBACK] Fallback usado: {_fallback_from} -> "
                    f"{_provider_used}/{_model_used}"
                )

            self.logger.info(
                f"[AGENT] Plano recebido | intent={plan.intent} | needs_tools={plan.needs_tools} "
                f"| risk={plan.risk_hint} | tools={len(plan.tools)}"
            )

            # Atualizar objetivo da sessão
            if plan.explanation:
                session_store.update_context(session.session_id, current_goal=plan.explanation[:200])

            # Se não precisa de tools, responder diretamente com explicação
            if not plan.needs_tools:
                self.logger.info("[AGENT] Sem tools, resposta final gerada.")
                response_text = _format_info_response(plan)
                session_store.add_message(session.session_id, "assistant", response_text, metadata={"model": self.model})
                self.logger.info(f"[AGENT] Concluído em {(time.monotonic()-_t0)*1000:.0f}ms")
                return ChatResponse(
                    session_id=session.session_id,
                    agent_id=self.id,
                    response=response_text,
                    status="completed",
                    model=_model_used,
                    execution_source="llm",
                    used_llm=True,
                    latency_ms=(time.monotonic() - _t0) * 1000,
                    metadata={
                        "provider": _provider_used,
                        "model": _model_used,
                        "fallback_used": _fallback_used,
                        "fallback_from": _fallback_from,
                    }
                )

            # Executar tools quando necessário
            tool_results = await self._execute_tools(plan, session)

            # Se há SQL no plano, processar via guard
            sql = plan.sql or _extract_sql_from_tools(plan)
            if sql:
                resp = await self._handle_sql(sql, plan, session, tool_results, run_id=run_id)
                resp.model = self.model
                resp.execution_source = "llm_with_tools"
                resp.used_llm = True
                resp.latency_ms = (time.monotonic() - _t0) * 1000
                self.logger.info(f"[AGENT] Concluído SQL em {resp.latency_ms:.0f}ms | status={resp.status}")
                return resp

            # Se chegou aqui, ferramentas foram executadas mas NÃO há SQL final.
            # Armazena os resultados das ferramentas no contexto como pensamento (e frontend não renderiza como resposta final)
            tool_response_text = _format_tool_result_response(plan, tool_results, max_rows=self.config.behavior.max_result_rows)
            session_store.add_message(
                session.session_id, 
                "system", 
                f"[RESULTADO DAS FERRAMENTAS]\n{tool_response_text}",
                metadata={"type": "thinking"}
            )
            
        # Limite atingido
        self.logger.warning(f"[AGENT] Máximo de passos ({max_steps}) atingido sem resposta final.")
        final_error = "[ERRO]\nO agente não conseguiu chegar a uma conclusão. Limite de passos atingido."
        session_store.add_message(session.session_id, "assistant", final_error, metadata={"model": self.model})
        return ChatResponse(
            session_id=session.session_id,
            agent_id=self.id,
            response=final_error,
            status="error",
            execution_source="fallback",
            used_llm=True,
            latency_ms=(time.monotonic() - _t0) * 1000
        )

    async def _execute_tools(self, plan: LLMPlan, session: Session) -> list[dict]:
        """Executa as tools indicadas no plano."""
        results = []
        max_steps = min(len(plan.tools), self.config.behavior.max_loop_steps)
        self.logger.info(f"[TOOLS] Executando {max_steps} tool(s) do plano")

        for i, tool_call in enumerate(plan.tools[:max_steps]):
            tool_name = tool_call.get("name", "")
            action = tool_call.get("action", "")
            tool_input = tool_call.get("input", {})

            self.logger.info(f"[TOOL {i+1}/{max_steps}] {tool_name}.{action} | input={tool_input}")

            result = await self._call_tool(tool_name, action, tool_input, session)

            success = result.get("success", False)
            rows_count = len(result.get("rows") or [])
            err = result.get("error", "")
            self.logger.info(
                f"[TOOL {i+1}/{max_steps}] resultado: success={success} "
                f"| rows={rows_count} | err='{err}'"
            )

            results.append({
                "tool": tool_name,
                "action": action,
                "result": result,
            })

            # Atualizar cache de objetos da sessão com resultados
            self._update_session_from_tool_result(session.session_id, action, result)

        return results

    async def _call_tool(self, tool_name: str, action: str, tool_input: dict, session: Session) -> dict:
        """
        Chama uma tool específica com validação.
        Tool principal: db_execute.
        Tools auxiliares: db_introspect, db_mockdata.
        """
        agent = self.config

        # ── db_execute ───────────────────────────────────────────
        if tool_name == "db_execute":
            sql = tool_input.get("sql") or action
            if not sql:
                return {"success": False, "error": "SQL não especificado para db_execute"}
            
            req = DBExecuteRequest(
                sql=sql,
                params=tool_input.get("params", {}),
                mode=tool_input.get("mode", "read"),
                dry_run=False,
            )
            result = db_execute.execute(req, agent)
            return result.model_dump()

        # ── db_introspect ────────────────────────────────────────
        elif tool_name in ("db_introspect", "db_introspection"):
            target = tool_input.get("target") or tool_input.get("table")
            result = db_introspection.introspect(agent, action, target)
            return result.model_dump()

        # ── db_mockdata ──────────────────────────────────────────
        elif tool_name == "db_mockdata":
            table = tool_input.get("table")
            rows = tool_input.get("rows", 10)
            dry_run = tool_input.get("dry_run", True)  # Default: dry_run para mockdata via plano
            
            if not table:
                return {"success": False, "error": "Tabela não especificada para db_mockdata"}
            
            result = generate_and_insert(agent, table, rows=rows, dry_run=dry_run)
            return result.model_dump()

        else:
            return {"success": False, "error": f"Tool desconhecida: {tool_name}"}

    async def _handle_sql(
        self,
        sql: str,
        plan: LLMPlan,
        session: Session,
        tool_results: list[dict],
        run_id: Optional[str] = None
    ) -> ChatResponse:
        """
        Processa SQL via guard engine.
        Cria pending action ou executa diretamente.
        """
        # Atualizar SQL gerado na sessão
        session_store.update_context(session.session_id, last_sql_generated=sql)

        # Avaliar risco com guard
        guard_decision = guard_engine.evaluate(sql, self.config)
        self.logger.info(
            f"[GUARD] allowed={guard_decision.allowed} | requires_confirmation={guard_decision.requires_confirmation} "
            f"| risk={guard_decision.risk_level} | reason='{guard_decision.reason}'"
        )

        if not guard_decision.allowed:
            # Bloqueado por permissão
            response_text = _format_blocked_response(sql, guard_decision.reason)
            session_store.add_message(session.session_id, "assistant", response_text)
            return ChatResponse(
                session_id=session.session_id,
                agent_id=self.id,
                response=response_text,
                sql_generated=sql,
                risk_level=guard_decision.risk_level,
                status="error",
            )

        if guard_decision.requires_confirmation:
            # Criar pending action
            classification = guard_decision.classification
            summary = _build_action_summary(sql, classification)
            
            pending_action = pa_store.create(
                agent_id=self.id,
                session_id=session.session_id,
                sql=sql,
                action_type=classification.sql_type,
                risk_level=guard_decision.risk_level,
                summary=summary,
                database=self.config.database.name,
            )

            # Registrar na sessão
            session_store.add_pending_action(session.session_id, {
                "id": pending_action.id,
                "summary": pending_action.summary,
                "risk_level": pending_action.risk_level,
            })

            response_text = _format_pending_response(
                sql=sql,
                pending_id=pending_action.id,
                risk_level=guard_decision.risk_level,
                summary=summary,
                plan=plan,
                guard_reason=guard_decision.reason,
            )
            session_store.add_message(session.session_id, "assistant", response_text, metadata={"model": self.model})

            return ChatResponse(
                session_id=session.session_id,
                agent_id=self.id,
                response=response_text,
                sql_generated=sql,
                pending_action_id=pending_action.id,
                risk_level=guard_decision.risk_level,
                status="pending_confirmation",
            )

        # Executar diretamente (risco baixo/médio aprovado)
        req = DBExecuteRequest(
            sql=sql,
            mode=_infer_mode(plan.intent),
        )
        exec_result = db_execute.execute(req, self.config)

        # Atualizar SQL executado na sessão
        if exec_result.success:
            session_store.update_context(session.session_id, last_sql_executed=sql)

        response_text = _format_execution_response(
            sql=sql,
            result=exec_result,
            plan=plan,
            tool_results=tool_results,
            max_rows=self.config.behavior.max_result_rows
        )
        session_store.add_message(session.session_id, "assistant", response_text, metadata={"model": self.model})

        if run_id: 
            # Injetar run_id no handle_sql se necessário, ou apenas emitir aqui
            target_step = "db_execute" if exec_result.success else "fallback"
            await progress_service.emit_step(session.session_id, run_id, target_step, status="completed" if exec_result.success else "failed")

        return ChatResponse(
            session_id=session.session_id,
            agent_id=self.id,
            response=response_text,
            sql_generated=sql,
            sql_executed=sql if exec_result.success else None,
            execution_result=exec_result.model_dump() if exec_result.success else None,
            risk_level=guard_decision.risk_level,
            status="completed" if exec_result.success else "error",
        )

    def _update_session_from_tool_result(self, session_id: str, action: str, result: dict) -> None:
        """Atualiza contexto da sessão com informações dos resultados das tools."""
        if not result.get("success"):
            return
        
        rows = result.get("rows", [])
        if not rows:
            return

        if action == "list_tables":
            tables = [list(row.values())[0] for row in rows if row]
            session_store.update_context(session_id, recent_tables=tables[:10])
        elif action == "list_views":
            views = [list(row.values())[0] for row in rows if row]
            session_store.update_context(session_id, recent_views=views[:5])
        elif action == "list_triggers":
            triggers = [row.get("Trigger", "") for row in rows if row]
            session_store.update_context(session_id, recent_triggers=triggers[:5])

    def _error_response(self, session: Session, error: str) -> ChatResponse:
        import time
        text = (
            f"[ERRO]\n{error}\n\n"
            f"[PRÓXIMO PASSO]\nVerifique se o Ollama está rodando com o modelo '{self.model}'."
        )
        session_store.add_message(session.session_id, "assistant", text, metadata={"model": self.model})
        return ChatResponse(
            session_id=session.session_id,
            agent_id=self.id,
            response=text,
            status="error",
            model=self.model,
            execution_source="fallback",
            used_llm=True
        )


# ─── Formatadores de resposta ──────────────────────────────────────────────

def _format_info_response(plan: LLMPlan) -> str:
    """Formata resposta informativa (sem execução)."""
    parts = []
    if plan.explanation:
        parts.append(f"[RESUMO]\n{plan.explanation}")
    if plan.sql:
        parts.append(f"[SQL]\n```sql\n{plan.sql}\n```\n\n[STATUS]\nNão executado")
    return "\n\n".join(parts) if parts else plan.explanation


def _format_tool_result_response(plan: LLMPlan, tool_results: list[dict], max_rows: int = 500) -> str:
    """Formata resposta com resultados de tools (sem SQL final)."""
    parts = []
    if plan.explanation:
        parts.append(f"[RESUMO]\n{plan.explanation}")

    for tr in tool_results:
        result = tr.get("result", {})
        if result.get("success") and result.get("rows"):
            rows = result["rows"]
            cols = result.get("columns", [])
            
            # Introspecção não deve ser truncada (describe, show create, list tables)
            limit = None if tr.get("action", "").startswith(("list", "describe", "show")) else max_rows
            
            formatted = format_rows(rows, cols, max_rows=limit)
            parts.append(f"[RESULTADO - {tr['action']}]\n{formatted}")
        elif not result.get("success"):
            parts.append(f"[ERRO - {tr['action']}]\n{result.get('error', 'Erro desconhecido')}")

    if not parts:
        parts.append("[RESULTADO]\nNenhum dado retornado")

    return "\n\n".join(parts)


def _format_execution_response(sql: str, result, plan: LLMPlan, tool_results: list[dict], max_rows: int = 500) -> str:
    """Formata resposta com resultado de execução."""
    parts = []

    if plan.explanation:
        parts.append(f"[RESUMO]\n{plan.explanation}")

    parts.append(f"[SQL]\n```sql\n{sql}\n```")

    if result.success:
        if result.rows:
            formatted = format_rows(result.rows, result.columns, max_rows=max_rows)
            rows_note = f" (resultado truncado em {max_rows} linhas)" if len(result.rows) > max_rows else ""
            parts.append(f"[RESULTADO]{rows_note}\n{formatted}")
        elif result.rows_affected is not None and result.rows_affected >= 0:
            parts.append(f"[RESULTADO]\n{result.rows_affected} linha(s) afetada(s)")

        parts.append(f"[STATUS]\nExecutado com sucesso ({result.execution_time_ms:.1f}ms)")
    else:
        parts.append(f"[ERRO]\n{result.error}")
        parts.append("[STATUS]\nFalhou")

    # Resultados de introspecção (se houver)
    for tr in tool_results:
        r = tr.get("result", {})
        if r.get("success") and r.get("rows") and tr.get("action", "").startswith("list_"):
            names = [list(row.values())[0] for row in r["rows"][:10] if row]
            parts.append(f"[INFO - {tr['action']}]\n{', '.join(str(n) for n in names)}")

    return "\n\n".join(parts)


def _format_pending_response(sql: str, pending_id: str, risk_level: str, summary: str, plan: LLMPlan, guard_reason: str) -> str:
    """Formata resposta when há pending action."""
    risk_upper = risk_level.upper()
    parts = [
        f"[RESUMO]\n{plan.explanation or summary}",
        f"[SQL]\n```sql\n{sql}\n```",
        f"[RISCO]\n{risk_upper}\n{guard_reason}",
        f"[AÇÃO NECESSÁRIA]\nConfirme para executar ou cancele esta operação.",
        f"[ID]\n{pending_id}",
        f"[PRÓXIMO PASSO]\nResponda 'confirmar {pending_id}' ou 'cancelar {pending_id}'",
    ]
    return "\n\n".join(parts)


def _format_blocked_response(sql: str, reason: str) -> str:
    """Formata resposta quando SQL foi bloqueado."""
    return (
        f"[ERRO]\nOperação bloqueada: {reason}\n\n"
        f"[SQL]\n```sql\n{sql}\n```\n\n"
        f"[STATUS]\nBloqueado pelo sistema de segurança"
    )





def _build_action_summary(sql: str, classification) -> str:
    """Constrói resumo legível da ação para a pending action."""
    sql_type = classification.sql_type
    objects = ", ".join(classification.affected_objects) if classification.affected_objects else "objeto(s)"
    
    summaries = {
        "DELETE": f"Deletar registros de {objects}",
        "DROP": f"Remover permanentemente {objects}",
        "TRUNCATE": f"Truncar tabela {objects} (remover todos os registros)",
        "UPDATE": f"Atualizar registros em {objects}",
        "ALTER": f"Alterar estrutura de {objects}",
    }
    
    base = summaries.get(sql_type, f"Executar {sql_type} em {objects}")
    if not classification.has_where and sql_type in ("DELETE", "UPDATE"):
        base += " (SEM cláusula WHERE — afeta TODOS os registros)"
    
    return base


def _extract_sql_from_tools(plan: LLMPlan) -> Optional[str]:
    """Extrai SQL de tool calls quando não está no campo sql do plano."""
    for tool in plan.tools:
        if tool.get("name") == "db_execute":
            return tool.get("input", {}).get("sql")
    return None


def _summarize_last_tool_results(session) -> str:
    """
    Extrai e formata os últimos resultados de ferramentas do histórico da sessão.
    Usado para passar dados reais para o LLM na 2ª+ iteração do loop.
    """
    tool_messages = [
        msg for msg in session.history
        if msg.role == "system" and msg.metadata.get("type") == "thinking"
    ]
    if not tool_messages:
        return "(nenhum resultado de ferramenta disponível ainda)"
    # Retorna apenas o resultado mais recente para não inflar o contexto
    last = tool_messages[-1]
    content = last.content
    # Remover o prefixo de marcação interna se presente
    if content.startswith("[RESULTADO DAS FERRAMENTAS]\n"):
        content = content[len("[RESULTADO DAS FERRAMENTAS]\n"):]
    return content[:3000]  # Limitar para não estourar contexto


def _infer_mode(intent: str) -> str:
    """Infere o mode de execução baseado no intent do plano."""
    if intent == "query":
        return "read"
    elif intent in ("write", "mockdata"):
        return "write"
    elif intent == "ddl":
        return "ddl"
    return "read"
