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
    Inicializa o banco de dados criando o schema e as tabelas se não existirem.
    """
    import mysql.connector
    from mysql.connector import errorcode

    # 1. Garantir que o Database existe (Provisionamento de Infra)
    try:
        # Tenta conectar sem banco de dados especificado para criar o schema
        tmp_conn = mysql.connector.connect(
            host=settings.MYSQL_HOST,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
            port=settings.MYSQL_PORT
        )
        cursor = tmp_conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {settings.MYSQL_DATABASE}")
        tmp_conn.close()
        logger.info(f"Database '{settings.MYSQL_DATABASE}' verificado/criado com sucesso.")
    except Exception as e:
        logger.error(f"Erro ao provisionar banco de dados MySQL: {str(e)}")
        # Não travamos o boot, deixamos o SQLAlchemy tentar a conexão normal abaixo

    # 2. Criar tabelas via SQLAlchemy
    try:
        # Importar modelos aqui para registrar no Base.metadata
        from app.db import models
        Base.metadata.create_all(bind=engine)
        logger.info("Tabelas do sistema inicializadas com sucesso.")

        # 3. Auto-Migração: Verificar colunas específicas (como 'icon')
        try:
            with engine.connect() as conn:
                # Verifica se a coluna 'icon' existe na tabela 'agents'
                result = conn.execute(text("SHOW COLUMNS FROM agents LIKE 'icon'"))
                if not result.fetchone():
                    logger.info("Coluna 'icon' não encontrada na tabela 'agents'. Adicionando...")
                    conn.execute(text("ALTER TABLE agents ADD COLUMN icon VARCHAR(20) DEFAULT '🤖' AFTER agent_type"))
                    conn.commit()
                    logger.info("Coluna 'icon' adicionada com sucesso.")
        except Exception as mig_err:
            logger.warning(f"Aviso na auto-migração: {mig_err}")

    except SQLAlchemyError as e:
        logger.error(f"Erro ao inicializar tabelas do banco: {str(e)}")
