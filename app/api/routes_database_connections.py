from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.platform import database_connection_service, agent_database_binding_service
from app.schemas.agent_bindings import AgentDatabaseBindingCreate
from app.core.logger import get_logger

logger = get_logger("api.routes_database_connections")

router = APIRouter(prefix="/api/database-connections", tags=["database-connections"])


@router.post("/", response_model=dict)
def api_create_connection(payload: dict, db: Session = Depends(get_db)):
    try:
        created = database_connection_service.create_connection(db, payload)
        return {"connection": {
            "id": created.id,
            "name": created.name,
            "db_type": created.db_type,
            "host": created.host,
            "port": created.port,
            "database_name": created.database_name,
            "username": created.username,
            "is_active": created.is_active,
        }}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=dict)
def api_list_connections(db: Session = Depends(get_db)):
    return {"connections": database_connection_service.list_connections(db)}


@router.get("/{id}")
def api_get_connection(id: int, db: Session = Depends(get_db)):
    c = database_connection_service.get_connection(db, id)
    if not c:
        raise HTTPException(status_code=404, detail="Connection not found")
    return {"connection": c}


@router.patch("/{id}/activate")
def api_activate(id: int, db: Session = Depends(get_db)):
    c = database_connection_service.activate_connection(db, id)
    if not c:
        raise HTTPException(status_code=404, detail="Connection not found")
    return {"connection": c}


@router.patch("/{id}/deactivate")
def api_deactivate(id: int, db: Session = Depends(get_db)):
    c = database_connection_service.deactivate_connection(db, id)
    if not c:
        raise HTTPException(status_code=404, detail="Connection not found")
    return {"connection": c}
