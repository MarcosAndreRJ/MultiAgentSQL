from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.platform import agent_database_binding_service
from app.core.logger import get_logger

logger = get_logger("api.routes_agent_db_bindings")

router = APIRouter(tags=["agent-database-bindings"])


@router.post("/api/agents/{agent_id}/database-bindings")
def api_create_agent_binding(agent_id: str, payload: dict, db: Session = Depends(get_db)):
    try:
        conn_id = payload.get("database_connection_id")
        is_default = bool(payload.get("is_default", False))
        access_mode = payload.get("access_mode", "readonly")
        schema_scope = payload.get("schema_scope")
        binding = agent_database_binding_service.bind_agent_to_connection(db, agent_id, conn_id, is_default, access_mode, schema_scope)
        return {"binding_id": binding.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/agents/{agent_id}/database-bindings")
def api_list_agent_bindings(agent_id: str, db: Session = Depends(get_db)):
    return {"bindings": agent_database_binding_service.list_agent_bindings(db, agent_id)}


@router.patch("/api/agent-database-bindings/{id}/set-default")
def api_set_default(id: int, db: Session = Depends(get_db)):
    b = agent_database_binding_service.set_binding_default(db, id)
    if not b:
        raise HTTPException(status_code=404, detail="Binding not found")
    return {"binding_id": b.id}


@router.patch("/api/agent-database-bindings/{id}/activate")
def api_activate(id: int, db: Session = Depends(get_db)):
    b = agent_database_binding_service.activate_binding(db, id)
    if not b:
        raise HTTPException(status_code=404, detail="Binding not found")
    return {"binding_id": b.id}


@router.patch("/api/agent-database-bindings/{id}/deactivate")
def api_deactivate(id: int, db: Session = Depends(get_db)):
    b = agent_database_binding_service.deactivate_binding(db, id)
    if not b:
        raise HTTPException(status_code=404, detail="Binding not found")
    return {"binding_id": b.id}
