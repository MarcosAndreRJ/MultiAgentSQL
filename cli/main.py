"""
MultiAgent SQL CLI
Utilitário de linha de comando com Typer para interagir com o sistema.
"""
import asyncio
import json
from typing import Optional

import typer
import httpx

app = typer.Typer(
    name="multiagent-sql",
    help="CLI para o sistema MultiAgent SQL",
    no_args_is_help=True,
)

API_BASE = "http://localhost:8000"
SESSION_ID = "cli-session"


def _get(path: str) -> dict:
    """GET para a API."""
    try:
        with httpx.Client(timeout=30) as client:
            res = client.get(f"{API_BASE}{path}")
            res.raise_for_status()
            return res.json()
    except httpx.ConnectError:
        typer.echo(f"❌ Não foi possível conectar à API em {API_BASE}", err=True)
        raise typer.Exit(1)


def _post(path: str, payload: dict) -> dict:
    """POST para a API."""
    try:
        with httpx.Client(timeout=120) as client:
            res = client.post(f"{API_BASE}{path}", json=payload)
            res.raise_for_status()
            return res.json()
    except httpx.ConnectError:
        typer.echo(f"❌ Não foi possível conectar à API em {API_BASE}", err=True)
        raise typer.Exit(1)


# ─── Agentes ───────────────────────────────────────────────────
@app.command("list-agents")
def list_agents():
    """Lista todos os agentes configurados."""
    agents = _get("/api/agents/")
    if not agents:
        typer.echo("Nenhum agente configurado.")
        return

    typer.echo("\n📋 AGENTES DISPONÍVEIS\n" + "─" * 50)
    for agent in agents:
        db = f" → {agent['database_name']}" if agent.get('database_name') else ""
        skills = ", ".join(agent.get('skills', [])) or "—"
        typer.echo(f"  {agent['id']:20} [{agent['type']:20}]{db}")
        typer.echo(f"    Nome:   {agent['name']}")
        typer.echo(f"    Modelo: {agent['model']}")
        typer.echo(f"    Skills: {skills}")
        typer.echo("")


@app.command("show-agent")
def show_agent(agent_id: str = typer.Argument(..., help="ID do agente")):
    """Exibe detalhes de um agente específico."""
    agent = _get(f"/api/agents/{agent_id}")
    
    typer.echo(f"\n🤖 AGENTE: {agent['id']}\n" + "─" * 50)
    typer.echo(f"  Nome:      {agent['name']}")
    typer.echo(f"  Tipo:      {agent['type']}")
    typer.echo(f"  Modelo:    {agent['model']}")
    typer.echo(f"  Banco:     {agent.get('database_name', 'N/A')}")
    typer.echo(f"  Skills:    {', '.join(agent.get('skills', []))}")
    
    if agent.get('guards'):
        guards = agent['guards'].get('require_confirmation_for', [])
        typer.echo(f"\n  ⚠️  Guard (confirmação obrigatória):")
        for g in guards:
            typer.echo(f"       - {g}")
    
    if agent.get('prompt_preview'):
        typer.echo(f"\n  📄 Prompt (preview):")
        typer.echo(f"     {agent['prompt_preview'][:300]}...")


@app.command("test-connection")
def test_connection(agent_id: str = typer.Argument(..., help="ID do agente especialista")):
    """Testa a conexão MySQL de um agente."""
    result = _get(f"/api/agents/{agent_id}/test-connection")
    if result.get('success'):
        typer.echo(f"✅ {result['message']}")
    else:
        typer.echo(f"❌ {result['message']}", err=True)


# ─── Chat ───────────────────────────────────────────────────────
@app.command("chat")
def chat(
    agent_id: str = typer.Argument(..., help="ID do agente"),
    session_id: str = typer.Option(SESSION_ID, "--session", "-s", help="ID da sessão"),
):
    """Inicia uma conversa interativa com um agente."""
    typer.echo(f"\n💬 Chat com agente '{agent_id}' (sessão: {session_id})")
    typer.echo("  Digite 'sair' para encerrar, 'reset' para limpar sessão\n")
    typer.echo("─" * 60)

    while True:
        try:
            user_input = input("Você: ").strip()
        except (KeyboardInterrupt, EOFError):
            typer.echo("\nEncerrado.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("sair", "exit", "quit"):
            break
        if user_input.lower() == "reset":
            _post(f"/api/chat/{session_id}", {})
            typer.echo("[Sistema] Sessão resetada.\n")
            continue

        try:
            resp = _post("/api/chat/", {
                "agent_id": agent_id,
                "session_id": session_id,
                "message": user_input,
            })
            typer.echo(f"\n{resp['response']}\n")
            typer.echo("─" * 60)
        except typer.Exit:
            break
        except Exception as e:
            typer.echo(f"❌ Erro: {e}\n")


@app.command("send")
def send(
    agent_id: str = typer.Argument(..., help="ID do agente"),
    message: str = typer.Argument(..., help="Mensagem a enviar"),
    session_id: str = typer.Option(SESSION_ID, "--session", "-s"),
):
    """Envia uma única mensagem para um agente."""
    resp = _post("/api/chat/", {
        "agent_id": agent_id,
        "session_id": session_id,
        "message": message,
    })
    typer.echo(resp['response'])
    if resp.get('pending_action_id'):
        typer.echo(f"\n⏳ Pending Action: {resp['pending_action_id']}")


# ─── Pending Actions ───────────────────────────────────────────
@app.command("list-pending")
def list_pending(
    agent_id: Optional[str] = typer.Option(None, "--agent", "-a"),
    session_id: Optional[str] = typer.Option(None, "--session", "-s"),
):
    """Lista pending actions."""
    params = []
    if agent_id:
        params.append(f"agent_id={agent_id}")
    if session_id:
        params.append(f"session_id={session_id}")
    
    query = "?" + "&".join(params) if params else ""
    data = _get(f"/api/pending/{query}")
    actions = [a for a in data.get('actions', []) if a.get('status') == 'pending']

    if not actions:
        typer.echo("Nenhuma pending action pendente.")
        return

    typer.echo(f"\n⏳ PENDING ACTIONS ({len(actions)})\n" + "─" * 60)
    for a in actions:
        typer.echo(f"  ID:      {a['id']}")
        typer.echo(f"  Agente:  {a['agent_id']}")
        typer.echo(f"  Banco:   {a.get('database', 'N/A')}")
        typer.echo(f"  Risco:   {a['risk_level'].upper()}")
        typer.echo(f"  Resumo:  {a['summary']}")
        typer.echo(f"  SQL:     {a['sql'][:100]}...")
        typer.echo(f"  Expira:  {a['expires_at']}")
        typer.echo("")


@app.command("confirm")
def confirm_pending(
    action_id: str = typer.Argument(..., help="ID da pending action"),
    agent_id: str = typer.Option(..., "--agent", "-a", help="ID do agente"),
    session_id: str = typer.Option(SESSION_ID, "--session", "-s"),
):
    """Confirma e executa uma pending action."""
    resp = _post("/api/chat/", {
        "agent_id": agent_id,
        "session_id": session_id,
        "message": f"confirmar {action_id}",
    })
    typer.echo(resp['response'])


@app.command("cancel")
def cancel_pending(
    action_id: str = typer.Argument(..., help="ID da pending action"),
    agent_id: str = typer.Option(..., "--agent", "-a"),
    session_id: str = typer.Option(SESSION_ID, "--session", "-s"),
):
    """Cancela uma pending action."""
    resp = _post("/api/chat/", {
        "agent_id": agent_id,
        "session_id": session_id,
        "message": f"cancelar {action_id}",
    })
    typer.echo(resp['response'])


# ─── Skills ────────────────────────────────────────────────────
@app.command("list-skills")
def list_skills(
    agent_id: Optional[str] = typer.Argument(None, help="ID do agente (opcional)"),
):
    """Lista skills disponíveis ou de um agente."""
    if agent_id:
        agent = _get(f"/api/agents/{agent_id}")
        skills = agent.get('skills', [])
        typer.echo(f"\n📚 Skills do agente '{agent_id}':")
        for s in skills:
            typer.echo(f"  - {s}")
    else:
        data = _get("/api/skills/")
        typer.echo(f"\n📚 SKILLS DISPONÍVEIS ({data['total']})\n" + "─" * 50)
        for skill in data['skills']:
            typer.echo(f"  {skill['id']:30} {skill.get('description', '')[:50]}")


@app.command("health")
def health():
    """Verifica o status da API."""
    data = _get("/health")
    typer.echo(f"✅ API OK | Agentes: {data['agents']} | IDs: {', '.join(data['agent_ids'])}")


if __name__ == "__main__":
    app()
