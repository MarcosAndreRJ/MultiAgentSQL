"""
MultiAgent SQL - FastAPI Application Entry Point
Runtime persistente com agentes independentes para operar bancos MySQL via LLMs locais.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core import agent_registry
from app.core.logger import get_logger
from app.tools.db_connection_manager import close_all
from app.db.session import init_db, SessionLocal
from app.services.dashboard import providers_service, models_service

logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Bootstrap e shutdown do runtime."""
    logger.info("=" * 60)
    logger.info("MultiAgent SQL - Iniciando...")
    logger.info("=" * 60)

    agent_registry.load_agents()
    agents = agent_registry.get_all()
    logger.info(f"Agentes carregados: {[a.id for a in agents]}")

    try:
        from app.services.ollama_client import check_connection

        available, msg = await check_connection()
        if available:
            logger.info(f"Ollama: {msg}")
        else:
            logger.warning(f"Ollama não disponível: {msg}")
    except Exception as exc:
        logger.warning(f"Não foi possível verificar Ollama: {exc}")

    # Inicializar Banco de Dados e Bootstrap (Resiliente)
    try:
        init_db()
        db = SessionLocal()
        try:
            await providers_service.bootstrap_providers(db)
            await models_service.bootstrap_models(db)
        finally:
            db.close()
    except Exception as db_exc:
        logger.error(f"Falha na conexão inicial com MySQL: {db_exc}")
        logger.warning("O dashboard poderá apresentar erros de dados, mas o chat continuará operando via fallback.")

    logger.info("MultiAgent SQL - Runtime pronto!")
    yield

    logger.info("MultiAgent SQL - Encerrando...")
    close_all()
    logger.info("Conexões encerradas. Bye!")


app = FastAPI(
    title="MultiAgent SQL",
    description="Sistema de múltiplos agentes independentes para operar bancos MySQL usando LLMs locais via Ollama.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers da API
from app.api.routes_agents import router as agents_router
from app.api.routes_aliases import router as aliases_router
from app.api.routes_chat import router as chat_router
from app.api.routes_diagram import router as diagram_router
from app.api.routes_digest import router as digest_router
from app.api.routes_execution import router as execution_router
from app.api.routes_pending import router as pending_router
from app.api.routes_skills import router as skills_router
from app.api.routes_upload import router as upload_router
from app.api.routes_providers import router as providers_router
from app.api.routes_models import router as models_router
from app.api.routes_health import router as health_router
from app.api.routes_config import router as config_router

app.include_router(agents_router)
app.include_router(chat_router)
app.include_router(execution_router)
app.include_router(pending_router)
app.include_router(skills_router)
app.include_router(digest_router)
app.include_router(aliases_router)
app.include_router(upload_router)
app.include_router(diagram_router)

# Rotas de Dashboard
app.include_router(providers_router)
app.include_router(models_router)
app.include_router(health_router)
app.include_router(config_router)


# Serve os assets do dashboard modular (CSS, JS, downloads)
public_dir = Path(__file__).parent.parent / "public"
if public_dir.exists():
    app.mount("/public", StaticFiles(directory=str(public_dir)), name="public")

# Serve assets legados do app/web/static (manter compatibilidade)
static_dir = Path(__file__).parent / "web" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")



@app.get("/health")
async def health():
    """Health check endpoint."""
    agents = agent_registry.get_all()
    return {
        "status": "ok",
        "agents": len(agents),
        "agent_ids": [a.id for a in agents],
    }


@app.get("/")
async def root():
    """Redireciona para a interface web."""
    from fastapi.responses import FileResponse

    template_path = Path(__file__).parent / "web" / "templates" / "index.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return {"message": "MultiAgent SQL API - Acesse /docs para a documentação"}


@app.get("/diagram/{agent_id}")
async def diagram_page(agent_id: str):
    """Serve a página de visualização estrutural."""
    from fastapi.responses import FileResponse

    template_path = Path(__file__).parent / "web" / "templates" / "diagram.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return {"message": "Página de diagrama não encontrada"}


if __name__ == "__main__":
    import uvicorn

    from app.core.settings import settings

    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
