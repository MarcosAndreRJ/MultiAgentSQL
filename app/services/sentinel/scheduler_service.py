"""
Service de Agendamento em Segundo Plano (Sentinel).
Executa o monitoramento periódico sem depender de workers externos.
"""
import asyncio
from datetime import datetime
from app.db.session import SessionLocal
from app.core.settings import settings
from app.core.logger import get_logger
from app.services.sentinel import provider_monitor_service, consistency_service

logger = get_logger("sentinel.scheduler")

# Variavel de controle para evitar execuções simultâneas
_sentinel_running = False

async def sentinel_scheduler_task():
    """Background task para execução periódica do Sentinel."""
    global _sentinel_running
    
    if not settings.SENTINEL_ENABLED:
        logger.info("Sentinel: Desativado nas configurações (SENTINEL_ENABLED=False).")
        return

    interval_seconds = settings.SENTINEL_INTERVAL_MINUTES * 60
    logger.info(f"Sentinel: Agendador iniciado (Intervalo: {settings.SENTINEL_INTERVAL_MINUTES} min).")

    # Espera um pouco inicial para o app estar PRONTO
    await asyncio.sleep(30)
    
    while True:
        try:
            if not _sentinel_running:
                _sentinel_running = True
                await run_sentinel_background()
                _sentinel_running = False
            
            logger.debug(f"Sentinel: Dormindo por {settings.SENTINEL_INTERVAL_MINUTES} minutos...")
            await asyncio.sleep(interval_seconds)
            
        except asyncio.CancelledError:
            logger.info("Sentinel: Agendador cancelado.")
            break
        except Exception as e:
            _sentinel_running = False
            logger.error(f"Sentinel: Erro no loop do agendador: {str(e)}")
            await asyncio.sleep(60) # Espera 1 min antes de tentar novamente se houver crash

async def run_sentinel_background():
    """Execução real do ciclo em background."""
    start_time = datetime.utcnow()
    logger.info(f"Sentinel: Iniciando ciclo periódico às {start_time.isoformat()}")
    
    db = SessionLocal()
    try:
        # 1. Monitoramento (Modelos e Créditos) - Chamada agora assíncrona
        monitor_results = await provider_monitor_service.run_sentinel_cycle(db)
        logger.info(f"Sentinel: Monitoramento concluído ({len(monitor_results)} providers).")
        
        # 2. Cálculo de Scores de Consistência

        consistency_service.update_consistency_scores(db)
        logger.info("Sentinel: Scores de consistência recalculados.")
        
    except Exception as e:
        logger.error(f"Sentinel: Falha na execução periódica: {str(e)}")
    finally:
        db.close()
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Sentinel: Ciclo finalizado em {elapsed:.2f}s.")

async def start_sentinel():
    """Inicia a task em background. Chamado pelo lifespan da app."""
    # A task não deve bloquear a inicialização da aplicação
    asyncio.create_task(sentinel_scheduler_task())
