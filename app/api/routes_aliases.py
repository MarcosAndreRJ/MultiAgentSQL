"""
API Routes: Table Aliases
GET    /api/aliases?agent_id=...                          — retorna aliases do agente
POST   /api/aliases/manual?agent_id=...                   — adiciona alias manual
DELETE /api/aliases/manual?agent_id=...&alias=@Dicas      — remove alias manual
"""
from fastapi import APIRouter, HTTPException, Query

from app.core import agent_registry
from app.core.logger import get_logger
from app.schemas.digest import AliasData, ManualAliasRequest
from app.services import alias_service

logger = get_logger("routes_aliases")

router = APIRouter(prefix="/api/aliases", tags=["aliases"])


def _assert_agent(agent_id: str):
    if not agent_registry.get(agent_id):
        raise HTTPException(status_code=404, detail=f"Agente '{agent_id}' não encontrado")


@router.get("/")
async def get_aliases(
    agent_id: str = Query(..., description="ID do agente"),
) -> AliasData:
    """Retorna todos os aliases (automáticos + manuais) do agente."""
    _assert_agent(agent_id)
    data = alias_service.load_aliases(agent_id)
    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"Aliases não encontrados para '{agent_id}'. Execute POST /api/digest/generate primeiro.",
        )
    return data


@router.post("/manual")
async def add_manual_alias(
    agent_id: str = Query(..., description="ID do agente"),
    body: ManualAliasRequest = ...,
) -> AliasData:
    """Adiciona ou sobrescreve um alias manual."""
    _assert_agent(agent_id)
    if not body.alias.startswith("@"):
        raise HTTPException(status_code=400, detail="O alias deve começar com '@', ex: @MinhaTabela")
    try:
        return alias_service.add_manual_alias(agent_id, body.alias, body.table_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/manual")
async def remove_manual_alias(
    agent_id: str = Query(..., description="ID do agente"),
    alias: str = Query(..., description="Token a remover, ex: @Dicas"),
) -> AliasData:
    """Remove um alias manual."""
    _assert_agent(agent_id)
    if not alias.startswith("@"):
        raise HTTPException(status_code=400, detail="O alias deve começar com '@'")
    try:
        return alias_service.remove_manual_alias(agent_id, alias)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggest")
async def suggest_aliases(
    agent_id: str = Query(..., description="ID do agente"),
    q: str = Query("", description="Prefixo para busca, ex: @cli"),
) -> list[dict]:
    """Retorna sugestões de aliases para autocomplete no chat."""
    _assert_agent(agent_id)
    if q and not q.startswith("@"):
        q = "@" + q
    return alias_service.suggest_aliases(agent_id, q)
