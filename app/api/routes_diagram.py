"""
API Routes: Diagram
GET  /api/diagram/{agent_id}
GET  /api/diagram/{agent_id}/status
GET  /api/diagram/{agent_id}/drafts
POST /api/diagram/{agent_id}/drafts
DELETE /api/diagram/{agent_id}/drafts/{table_name}
POST /api/diagram/{agent_id}/execute-ddl
"""
import re

from fastapi import APIRouter, HTTPException

from app.core import agent_registry
from app.core.logger import get_logger
from app.schemas.diagram import DiagramPayload, DiagramStatus
from app.schemas.draft import AddDraftTableRequest, DiagramDraft, DraftTable
from app.schemas.execution import DBExecuteRequest
from app.services import diagram_draft_service, diagram_service
from app.services.diagram_service import DiagramDigestInvalidError, DiagramDigestNotFoundError
from app.tools import db_execute
from pydantic import BaseModel

logger = get_logger("routes_diagram")

router = APIRouter(prefix="/api/diagram", tags=["diagram"])

# DDL statements permitidos neste endpoint (somente CREATE TABLE)
_DDL_ALLOWED = re.compile(r"^\s*CREATE\s+TABLE\b", re.IGNORECASE)
# Padrões proibidos — prevenção básica contra injeção de multi-statements
_DDL_BLOCKED = re.compile(r";.*(DROP|DELETE|TRUNCATE|INSERT|UPDATE|GRANT|REVOKE)", re.IGNORECASE | re.DOTALL)


class ExecuteDDLRequest(BaseModel):
    sql: str
    # Se True, remove o draft correspondente ao nome da tabela após sucesso
    promote_draft: str | None = None


def _get_agent(agent_id: str):
    config = agent_registry.get(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Agente '{agent_id}' nao encontrado")
    return config


# ── Diagram ───────────────────────────────────────────────────────────────────

@router.get("/{agent_id}/status")
async def get_diagram_status(agent_id: str) -> DiagramStatus:
    """Retorna status de disponibilidade/validade do digest para diagrama."""
    config = _get_agent(agent_id)
    return diagram_service.get_diagram_status(agent_id=agent_id, agent_name=config.name)


@router.get("/{agent_id}")
async def get_diagram(agent_id: str) -> DiagramPayload:
    """Retorna grafo estrutural mesclando digest real + drafts visuais."""
    config = _get_agent(agent_id)
    try:
        return diagram_service.build_diagram(agent_id=agent_id, agent_name=config.name)
    except DiagramDigestNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Digest nao encontrado. Gere o digest antes de visualizar a estrutura.",
        )
    except DiagramDigestInvalidError:
        raise HTTPException(
            status_code=422,
            detail="Digest invalido. Gere o digest novamente antes de visualizar a estrutura.",
        )
    except Exception as exc:
        logger.error(f"[DIAGRAM] Erro ao montar diagrama para '{agent_id}': {exc}")
        raise HTTPException(status_code=500, detail="Falha ao montar diagrama estrutural.")


# ── Drafts ───────────────────────────────────────────────────────────────────

@router.get("/{agent_id}/drafts")
async def list_drafts(agent_id: str) -> DiagramDraft:
    """Retorna todos os rascunhos visuais do agente."""
    _get_agent(agent_id)
    return diagram_draft_service.get_draft(agent_id)


@router.post("/{agent_id}/drafts", status_code=201)
async def add_draft_table(agent_id: str, body: AddDraftTableRequest) -> DraftTable:
    """
    Cria ou substitui uma tabela de rascunho no ERD.
    Não toca no banco de dados — apenas persiste o modelo visual.
    """
    _get_agent(agent_id)

    if not body.name or not body.name.strip():
        raise HTTPException(status_code=400, detail="Nome da tabela nao pode ser vazio.")
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", body.name):
        raise HTTPException(
            status_code=400,
            detail="Nome de tabela invalido. Use apenas letras, numeros e underscore.",
        )
    if len(body.columns) == 0:
        raise HTTPException(status_code=400, detail="A tabela deve ter ao menos uma coluna.")

    return diagram_draft_service.add_table(agent_id, body)


@router.delete("/{agent_id}/drafts/{table_name}", status_code=200)
async def remove_draft_table(agent_id: str, table_name: str):
    """Remove um rascunho de tabela pelo nome."""
    _get_agent(agent_id)
    removed = diagram_draft_service.remove_table(agent_id, table_name)
    if not removed:
        raise HTTPException(
            status_code=404,
            detail=f"Draft '{table_name}' nao encontrado para o agente '{agent_id}'.",
        )
    return {"success": True, "message": f"Draft '{table_name}' removido."}


# ── Execute DDL ───────────────────────────────────────────────────────────────

@router.post("/{agent_id}/execute-ddl")
async def execute_ddl(agent_id: str, body: ExecuteDDLRequest):
    """
    Executa um CREATE TABLE no banco vinculado ao agente.
    Aceita apenas DDL CREATE TABLE.
    Se promote_draft for informado, remove o draft correspondente após sucesso.
    """
    config = _get_agent(agent_id)

    sql = (body.sql or "").strip()
    if not sql:
        raise HTTPException(status_code=400, detail="SQL nao pode ser vazio.")

    if not _DDL_ALLOWED.match(sql):
        raise HTTPException(
            status_code=400,
            detail="Apenas CREATE TABLE e permitido neste endpoint.",
        )

    if _DDL_BLOCKED.search(sql):
        raise HTTPException(
            status_code=400,
            detail="SQL contem instrucoes nao permitidas.",
        )

    result = db_execute.execute(
        DBExecuteRequest(sql=sql, mode="ddl"),
        config,
    )

    if not result.success:
        logger.warning(f"[DIAGRAM DDL] Falha | agente={agent_id} | erro={result.error}")
        raise HTTPException(status_code=400, detail=result.error or "Falha ao executar DDL.")

    # Promover draft (se solicitado) — move tabela do estado visual para real
    if body.promote_draft:
        promoted = diagram_draft_service.promote_table(agent_id, body.promote_draft)
        logger.info(f"[DIAGRAM DDL] Draft promovido={promoted} | tabela={body.promote_draft}")

    logger.info(f"[DIAGRAM DDL] CREATE TABLE executado | agente={agent_id}")
    return {"success": True, "message": "Tabela criada com sucesso no banco."}

