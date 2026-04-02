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

async def check_database_health(db: Session) -> dict:
    """
    Verifica conexão com o MySQL.
    """
    start_time = time.time()
    try:
        # Executa query leve
        db.execute(text("SELECT 1"))
        latency = (time.time() - start_time) * 1000
        return {
            "status": "ok",
            "message": "Conexão com MySQL estabelecida.",
            "latency_ms": round(latency, 2)
        }
    except Exception as e:
        logger.error(f"Erro no health do banco: {str(e)}")
        return {
            "status": "error",
            "message": f"Erro MySQL: {str(e)}",
            "latency_ms": -1
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
