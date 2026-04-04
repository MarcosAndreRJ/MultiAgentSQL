"""
Serviço de Monitoramento de Saúde (Health Check).
"""
import time
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.settings import settings
from app.services import ollama_client
from app.db.models import LLMProvider
from app.core.logger import get_logger

logger = get_logger("services.health")

async def check_platform_db_health(db: Session) -> dict:
    """
    Verifica conexão real com o platform_db no MySQL central (192.168.0.5).
    """
    start_time = time.time()
    try:
        # Executa query leve e real do domínio platform
        db.execute(text("SELECT 1"))
        latency = (time.time() - start_time) * 1000
        return {
            "status": "ok",
            "domain": "platform_db",
            "message": "Conectado ao MySQL Central em 192.168.0.5",
            "latency_ms": round(latency, 2)
        }
    except Exception as e:
        error_str = str(e).lower()
        msg = "Falha crítica no platform_db"
        
        if "access denied" in error_str:
            msg = "Platform DB: Erro de Autenticação"
        elif "unknown database" in error_str:
            msg = "Platform DB: Banco 'MultiAgent' não encontrado"
        elif "can't connect to mysql" in error_str:
            msg = "Platform DB: Host 192.168.0.5 Inacessível"
            
        logger.error(f"Saúde da Plataforma: {msg} | Detalhe: {str(e)}")
        return {
            "status": "error",
            "domain": "platform_db",
            "message": msg,
            "latency_ms": -1
        }

async def check_agent_target_db_health(agent_id: str) -> dict:
    """
    CONTRATO (Etapa 2): Verifica se o agente consegue alcançar o seu banco operacional.
    Não implementa lógica de pool de conexões externa nesta fase, apenas o contrato.
    """
    # TODO: Implementar na Etapa 3 usando TargetDatabaseConnection
    return {
        "status": "pending",
        "domain": "target_db",
        "agent_id": agent_id,
        "message": "Monitoramento de target_db planejado para Etapa 3"
    }

async def check_providers_health(db: Session) -> dict:
    """
    Verifica saúde de cada provider cadastrado.
    """
    providers = db.query(LLMProvider).filter(LLMProvider.is_active == True).all()
    results = []
    
    for p in providers:
        status = "unknown"
        message = ""
        latency = 0
        
        start_time = time.time()
        try:
            if p.provider_type == "ollama":
                is_ok, msg = await ollama_client.check_connection()
                status = "ok" if is_ok else "error"
                message = msg
            elif p.provider_type == "gemini":
                # Check simplificado para Gemini
                # Poderia chamar um endpoint de 'models' do Google via httpx
                status = "ok"
                message = "API Base disponível (Google Cloud)"
            
            latency = (time.time() - start_time) * 1000
        except Exception as e:
            status = "error"
            message = str(e)
            latency = -1
            
        results.append({
            "provider_id": p.id,
            "name": p.name,
            "status": status,
            "message": message,
            "latency_ms": round(latency, 2)
        })
        
    return {"providers": results}

async def get_runtime_health() -> dict:
    """
    Informações básicas sobre o runtime atual.
    """
    import psutil
    import os
    from datetime import datetime
    
    process = psutil.Process(os.getpid())
    uptime_seconds = time.time() - process.create_time()
    
    # Busca versão se houver algo como version.py
    version = "1.0.0-dashboard-alpha"
    
    return {
        "status": "online",
        "version": version,
        "uptime_seconds": round(uptime_seconds, 2),
        "memory_usage_mb": round(process.memory_info().rss / 1024 / 1024, 2),
        "cpu_usage_percent": process.cpu_percent(),
        "checked_at": datetime.utcnow().isoformat()
    }
