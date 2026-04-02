"""
Prompt Builder: constrói o prompt final para o agente.

PROMPT FINAL = prompt_base + skills + digest_summary + digest_section_relevante
             + contexto da sessão + histórico + mensagem do usuário
"""
from pathlib import Path
from typing import Optional

from app.core.logger import get_logger
from app.core.settings import settings
from app.schemas.agent import AgentConfig
from app.schemas.chat import Session, HistoryMessage
from app.agents.skill_loader import load_skills_for_agent

logger = get_logger("prompt_builder")


# ─── Digest Context ────────────────────────────────────────────────────────────

def build_digest_context(
    agent_id: str,
    user_message: str,
    resolved_tables: Optional[list[str]] = None,
) -> str:
    """
    Constrói o bloco de contexto do digest para o prompt.

    Estratégia:
    - Sempre injeta um resumo curto (tabelas/views/triggers)
    - Se a mensagem ou aliases resolvidos citam uma tabela específica,
      injeta a seção detalhada daquela tabela
    - Não injeta o digest inteiro (evita inflação de prompt)
    """
    try:
        from app.services.digest_service import load_digest
    except ImportError:
        return ""

    digest = load_digest(agent_id)
    if not digest:
        return ""

    # Resumo sempre incluído (curto)
    s = digest.summary
    parts: list[str] = [
        "# CONTEXTO DO BANCO (DB Digest)",
        f"**Banco:** `{digest.database}` | "
        f"Tabelas: {s.tables} | Views: {s.views} | "
        f"Triggers: {s.triggers} | Procedures: {s.procedures} | Functions: {s.functions}",
    ]

    if digest.tables:
        table_list = ", ".join(f"`{t.name}`" for t in digest.tables[:20])
        parts.append(f"**Tabelas disponíveis:** {table_list}")

    # Identificar quais tabelas são relevantes para a mensagem
    relevant_tables = _find_relevant_tables(user_message, digest, resolved_tables)

    # Injetar seção detalhada das tabelas relevantes (máx 3)
    if relevant_tables:
        parts.append("\n## Detalhes das Tabelas Relevantes")
        for tname in relevant_tables[:3]:
            section = _build_table_section(tname, digest)
            if section:
                parts.append(section)

    return "\n".join(parts)


def _find_relevant_tables(
    message: str,
    digest,
    resolved_tables: Optional[list[str]],
) -> list[str]:
    """Detecta tabelas mencionadas na mensagem (case-insensitive)."""
    all_names = {t.name.lower(): t.name for t in digest.tables}
    all_names.update({v.name.lower(): v.name for v in digest.views})

    found: list[str] = []

    # Tabelas resolvidas via aliases têm prioridade
    if resolved_tables:
        for name in resolved_tables:
            if name.lower() in all_names:
                real = all_names[name.lower()]
                if real not in found:
                    found.append(real)

    # Busca direta na mensagem
    msg_lower = message.lower()
    for lower_name, real_name in all_names.items():
        if lower_name in msg_lower and real_name not in found:
            found.append(real_name)

    return found


def _build_table_section(table_name: str, digest) -> str:
    """Gera bloco Markdown resumido para uma tabela específica."""
    table = next(
        (t for t in [*digest.tables, *digest.views] if t.name == table_name), None
    )
    if not table:
        return ""

    lines = [f"\n### `{table.name}` ({table.type})"]
    if table.description:
        lines.append(f"_{table.description}_")
    if table.primary_key:
        lines.append(f"**PK:** `{table.primary_key}`")
    if table.columns:
        col_parts = [f"`{c.name}` {c.type}" for c in table.columns[:15]]
        lines.append("**Colunas:** " + ", ".join(col_parts))
        if len(table.columns) > 15:
            lines.append(f"_(+ {len(table.columns) - 15} colunas omitidas)_")
    if table.foreign_keys:
        fk_parts = [f"`{fk.column}` → `{fk.ref_table}`" for fk in table.foreign_keys[:5]]
        lines.append("**FKs:** " + ", ".join(fk_parts))
    return "\n".join(lines)


def load_base_prompt(agent: AgentConfig) -> str:
    """
    Carrega e renderiza o prompt base do agente.
    Substitui variáveis como {database_name} com valores reais.
    """
    if not agent.prompt_file:
        return _default_prompt(agent)

    prompt_file = settings.prompts_path / agent.prompt_file
    if not prompt_file.exists():
        logger.warning(f"Arquivo de prompt não encontrado: {prompt_file}")
        return _default_prompt(agent)

    try:
        content = prompt_file.read_text(encoding="utf-8")
        
        # Substituir variáveis de template
        if agent.database:
            content = content.replace("{database_name}", agent.database.name)
            content = content.replace("{database_host}", agent.database.host)
        
        return content
    except Exception as e:
        logger.error(f"Erro ao carregar prompt '{agent.prompt_file}': {e}")
        return _default_prompt(agent)


def build_context_block(session: Session) -> str:
    """
    Constrói o bloco de contexto da sessão para incluir no prompt.
    Inclui: objetivo atual, objetos recentes, SQLs recentes, pending actions.
    """
    parts = []

    if session.current_goal:
        parts.append(f"## Objetivo Atual\n{session.current_goal}")

    recent_objs = session.recent_objects
    if any(recent_objs.get(k) for k in ("tables", "views", "triggers")):
        obj_parts = []
        if recent_objs.get("tables"):
            obj_parts.append(f"Tabelas: {', '.join(recent_objs['tables'][:5])}")
        if recent_objs.get("views"):
            obj_parts.append(f"Views: {', '.join(recent_objs['views'][:3])}")
        if recent_objs.get("triggers"):
            obj_parts.append(f"Triggers: {', '.join(recent_objs['triggers'][:3])}")
        parts.append("## Objetos Recentes\n" + "\n".join(obj_parts))

    if session.last_sql_generated:
        truncated = session.last_sql_generated[:500]
        parts.append(f"## Último SQL Gerado\n```sql\n{truncated}\n```")

    if session.pending_actions:
        pa_summaries = [f"- {pa.get('id')}: {pa.get('summary')}" for pa in session.pending_actions[:5]]
        parts.append("## Ações Pendentes de Confirmação\n" + "\n".join(pa_summaries))

    if parts:
        return "# CONTEXTO DA SESSÃO\n\n" + "\n\n".join(parts)
    return ""


def build_history_block(history: list[HistoryMessage], max_messages: int = 10) -> str:
    """
    Formata o histórico recente da conversa.
    
    Args:
        history: Lista de mensagens históricas.
        max_messages: Máximo de mensagens a incluir.
    """
    if not history:
        return ""

    recent = history[-max_messages:]
    parts = ["# HISTÓRICO RECENTE DA CONVERSA"]

    # Separar mensagens de resultado de tools das demais
    tool_results = [m for m in recent if m.role == "system" and m.metadata.get("type") == "thinking"]
    other_messages = [m for m in recent if not (m.role == "system" and m.metadata.get("type") == "thinking")]

    # Histórico de conversa normal (sem tool results)
    for msg in other_messages:
        if msg.role == "user":
            role_label = "USUÁRIO (mensagem passada)"
            limit = 1000
        elif msg.role == "system":
            role_label = "SISTEMA"
            limit = 2000
        else:
            role_label = "AGENTE (resposta passada — NÃO contém dados desta execução)"
            limit = 2000

        content = msg.content[:limit] + "..." if len(msg.content) > limit else msg.content
        parts.append(f"**{role_label}:** {content}")

    # Resultado de tools atual (se houver) — destacado com aviso especial
    if tool_results:
        parts.append("\n# RESULTADO DE FERRAMENTA (dados reais do banco, obtidos AGORA nesta execução)")
        for msg in tool_results[-1:]:  # Apenas o resultado mais recente
            content = msg.content[:4000] + "..." if len(msg.content) > 4000 else msg.content
            parts.append(content)

    return "\n\n".join(parts)


def build_full_prompt(
    agent: AgentConfig,
    session: Session,
    user_message: str,
    resolved_tables: Optional[list[str]] = None,
) -> str:
    """
    Constrói o prompt final completo.
    
    PROMPT FINAL =
    prompt_base
    + skills
    + digest_summary (seletivo)
    + context da sessão
    + histórico
    + mensagem do usuário
    """
    sections = []

    # 1. Prompt base do agente
    base_prompt = load_base_prompt(agent)
    if base_prompt:
        sections.append(base_prompt)

    # 2. Skills do agente
    if agent.skills:
        skills_text = load_skills_for_agent(agent.skills)
        if skills_text:
            sections.append("# SKILLS DO AGENTE\n\n" + skills_text)

    # 3. Contexto do Digest (apenas para agentes com banco de dados)
    if agent.database and agent.type != "principal":
        digest_ctx = build_digest_context(agent.id, user_message, resolved_tables)
        if digest_ctx:
            sections.append(digest_ctx)

    # 4. Contexto da sessão
    context = build_context_block(session)
    if context:
        sections.append(context)

    # 5. Histórico recente
    history_block = build_history_block(session.history)
    if history_block:
        sections.append(history_block)

    # 6. Mensagem atual do usuário
    sections.append(f"# MENSAGEM ATUAL DO USUÁRIO\n\n{user_message}")

    return "\n\n---\n\n".join(sections)


def _default_prompt(agent: AgentConfig) -> str:
    """Prompt base padrão quando o arquivo de prompt não é encontrado."""
    if agent.type == "principal":
        return (
            f"Você é {agent.name}, um assistente técnico generalista especializado em MySQL. "
            "Você não executa comandos em banco de dados. "
            "Responda de forma técnica, clara e objetiva em português brasileiro."
        )
    else:
        db_name = agent.database.name if agent.database else "desconhecido"
        return (
            f"Você é {agent.name}, um agente especialista MySQL vinculado ao banco '{db_name}'. "
            "Você é um executor técnico assistido. "
            "Não invente schema. "
            "Consulte tools antes de afirmar. "
            "Nunca diga que executou sem retorno real. "
            "Responda em português brasileiro."
        )
