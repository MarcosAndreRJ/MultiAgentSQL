"""
API Routes: Operações dinâmicas sobre o Banco Alvo (Target DB) do Agente.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.services import agent_service
from app.services.target_db import introspection_service, query_service

router = APIRouter(prefix="/agents", tags=["Target DB"])

class QueryRequest(BaseModel):
    """Corpo da requisição para execução de query."""
    query: str

@router.get("/{agent_id}/target-db/test")
async def test_agent_target_db(agent_id: str):
    """
    Testa a conectividade real do banco operacional do agente.
    """
    result = await agent_service.test_agent_target_db_connection(agent_id)
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result)
    return result

@router.get("/{agent_id}/target-db/tables")
async def list_agent_tables(agent_id: str):
    """
    Lista as tabelas disponíveis para introspecção do agente.
    """
    try:
        tables = introspection_service.list_tables(agent_id)
        return {"agent_id": agent_id, "tables": tables}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao listar tabelas: {str(e)}")

@router.get("/{agent_id}/target-db/tables/{table}")
async def describe_agent_table(agent_id: str, table: str):
    """
    Retorna a estrutura detalhada de uma tabela do agente.
    """
    try:
        return introspection_service.describe_table(agent_id, table)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao descrever tabela: {str(e)}")

@router.post("/{agent_id}/target-db/query")
async def execute_agent_query(agent_id: str, request: QueryRequest):
    """
    Executa uma query SELECT segura no banco operacional do agente.
    """
    try:
        return query_service.execute_read_query(agent_id, request.query)
    except ValueError as ve:
        # Erro de validação de segurança ou sintaxe
        raise HTTPException(status_code=403, detail=str(ve))
    except Exception as e:
        # Erro de execução no banco
        raise HTTPException(status_code=400, detail=f"Erro na execução SQL: {str(e)}")
