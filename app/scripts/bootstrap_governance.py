"""
Script de Bootstrap para Migração de Governança.
Importa os agentes do agent_registry (YAML) para a tabela 'agents' no platform_db.
"""
import sys
import os
from pathlib import Path

# Adiciona a raiz do projeto ao sys.path para imports funcionarem
sys.path.append(os.getcwd())

from app.db.session import SessionLocal, init_db
from app.core import agent_registry
from app.services.platform import agent_governance_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bootstrap.governance")

def run_bootstrap():
    logger.info("Iniciando Bootstrap de Governança...")
    
    # Garantir que o Registry YAML está carregado
    agent_registry.load_agents()
    
    db = SessionLocal()
    try:
        # 1. Executar o bootstrap de agentes
        stats = agent_governance_service.bootstrap_governance_from_yaml(db)
        logger.info(f"Bootstrap completo! Resultados: {stats}")
        
    except Exception as e:
        logger.error(f"Erro fatal no bootstrap de governança: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_bootstrap()
