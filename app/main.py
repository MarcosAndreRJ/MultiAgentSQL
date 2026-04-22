"""
MultiAgent SQL - FastAPI Application Entry Point
Runtime persistente com agentes independentes para operar bancos MySQL via LLMs locais.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core import agent_registry
from app.core.logger import get_logger
from app.tools.db_connection_manager import close_all
from app.db.session import init_db, SessionLocal
from sqlalchemy.exc import SQLAlchemyError
from app.services.dashboard import providers_service, models_service
from app.services.sentinel.scheduler_service import start_sentinel

logger = get_logger("app")


# Patch para garantir que o Windows sirva arquivos estáticos com charset UTF-8

# Patch para garantir que o Windows sirva arquivos estáticos com charset UTF-8
# Sem isso, navegadores podem interpretar emojis e acentos como Windows-1252/ISO-8859-1
import mimetypes
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('text/html', '.html')
mimetypes.types_map['.js'] = 'application/javascript; charset=utf-8'
mimetypes.types_map['.css'] = 'text/css; charset=utf-8'
mimetypes.types_map['.html'] = 'text/html; charset=utf-8'



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

    # Inicializar Banco de Dados e Bootstrap (Fundação de Infra)
    try:
        init_db()
        db = SessionLocal()
        try:
            await providers_service.bootstrap_providers(db)
            await models_service.bootstrap_models(db)
            logger.info("Fundação MySQL: Sincronizada e PRONTA em 192.168.0.5")
        finally:
            db.close()
            
        # Iniciar Scheduler do Sentinel (Segundo Plano)
        await start_sentinel()
        
    except Exception as db_exc:
        logger.error(f"FALHA NA FUNDAÇÃO MYSQL: {db_exc}")
        logger.warning("MODO DEGRADADO: Dashboard limitado ao cache local. Chat opera via fallback YAML.")

    logger.info("MultiAgent SQL - Sistema Operacional!")
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

# Patch de Middleware para forçar charset UTF-8 em arquivos estáticos (.js, .css, .html)
# Isso resolve o problema de caracteres corrompidos no Windows/FastAPI
@app.middleware("http")
async def add_charset_middleware(request: Request, call_next):
    response = await call_next(request)
    content_type = response.headers.get("Content-Type", "")
    # Se for um arquivo estático conhecido e não tiver charset, injeta UTF-8
    if any(m in content_type for m in ["javascript", "css", "html"]) and "charset" not in content_type:
        response.headers["Content-Type"] = f"{content_type}; charset=utf-8"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handler global para erros 422 do Pydantic.
    Transforma erros técnicos em mensagens compreensíveis para o dashboard.
    """
    errors = []
    for error in exc.errors():
        # Ex: "body -> type: field required"
        field = " -> ".join([str(x) for x in error.get("loc", []) if x != "body"])
        msg = error.get("msg")
        errors.append(f"**{field}**: {msg}")
    
    friendly_msg = "Falha na validação dos dados: " + " | ".join(errors)
    logger.warning(f"Erro 422: {friendly_msg}")
    
    return JSONResponse(
        status_code=422,
        content={"detail": friendly_msg},
    )


@app.exception_handler(ConnectionError)
async def db_connection_exception_handler(request: Request, exc: ConnectionError):
    """Handler para erros de conexão (ex: banco offline)."""
    logger.error(f"Erro de conexão detectado: {exc}")
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc)},
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handler para erros gerais do SQLAlchemy."""
    logger.error(f"Erro de banco de dados (SQLAlchemy): {exc}")
    # Se for falha crítica de conexão, retornamos 503
    if "Connection refused" in str(exc) or "2003" in str(exc) or "Can't connect" in str(exc):
        return JSONResponse(
            status_code=503,
            content={"detail": "O banco de dados de plataforma (192.168.0.5) não está respondendo. Verifique se o serviço MySQL está ativo e se o firewall permite conexões externas."},
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno no processamento do banco de dados."},
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
from app.api.routes_target_db import router as target_db_router
from app.api.routes_providers_v2 import router as providers_v2_router
from app.api.routes_database_connections import router as db_connections_router
from app.api.routes_agent_database_bindings import router as agent_db_bindings_router
from app.api.routes_observability import router as observability_router
from app.api.routes_sentinel import router as sentinel_router

app.include_router(agents_router)
app.include_router(chat_router)
app.include_router(execution_router)
app.include_router(pending_router)
app.include_router(skills_router)
app.include_router(digest_router)
app.include_router(aliases_router)
app.include_router(upload_router)
app.include_router(diagram_router)

# Incluir routers operacionais e de gestão
app.include_router(target_db_router, prefix="/api", tags=["Agente - Target DB"])
app.include_router(providers_v2_router, tags=["Provedores LLM"])
app.include_router(db_connections_router)
app.include_router(agent_db_bindings_router)
app.include_router(providers_router)
app.include_router(models_router)
app.include_router(health_router)
app.include_router(observability_router)
app.include_router(sentinel_router)
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
