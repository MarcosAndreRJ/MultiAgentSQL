"""
Configuração do SQLAlchemy e Sessão do MySQL.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError

from app.core.settings import settings
from app.core.logger import get_logger

logger = get_logger("db.session")

# Engine do Banco de Dados
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Verifica se a conexão está viva antes de usar
    pool_recycle=3600,   # Recicla conexões a cada 1h para evitar timeout do MySQL
)

# Fábrica de Sessões
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Classe Base para Modelos
Base = declarative_base()

def get_db():
    """
    Dependency Generator para injeção de dependência do FastAPI.
    Garante que a sessão seja fechada após a requisição.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Inicializa o banco de dados criando as tabelas se não existirem.
    """
    try:
        # Importar modelos aqui para registrar no Base.metadata
        from app.db import models
        Base.metadata.create_all(bind=engine)
        logger.info("Banco de dados inicializado com sucesso (ou tabelas já existiam).")
    except SQLAlchemyError as e:
        logger.error(f"Erro ao inicializar banco de dados: {str(e)}")
        # Não levantamos erro para não travar o app se o banco estiver offline no boot
        # mas as rotas de API irão falhar graciosamente depois.
