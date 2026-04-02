"""
API Routes: Execution
POST /api/execute - executa SQL diretamente (sem agent loop)
GET /api/execute/history - histórico de execuções
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import execution_service

router = APIRouter(prefix="/api/execute", tags=["execution"])


class ExecuteRequest(BaseModel):
    agent_id: str
    session_id: str = "api-direct"
    sql: str
    skip_guard: bool = False


@router.post("/")
async def execute_sql(req: ExecuteRequest):
    """Executa SQL diretamente para um agente."""
    if not req.sql.strip():
        raise HTTPException(status_code=400, detail="SQL não pode estar vazio")
    
    result = await execution_service.execute_sql(
        agent_id=req.agent_id,
        sql=req.sql,
        session_id=req.session_id,
        skip_guard=req.skip_guard,
    )
    return result


@router.get("/history")
async def get_history(agent_id: Optional[str] = None, limit: int = 50):
    """Histórico de execuções."""
    records = execution_service.get_execution_history(agent_id=agent_id, limit=limit)
    return {"records": records, "total": len(records)}
