"""
Gerenciador de Conexões (Cache) para Target DB.
Garante reutilização e isolamento de engines por Agente.
"""
from typing import Dict, Optional
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.services.platform import agent_database_binding_service
from app.services.target_db.connection_factory import create_target_engine
from app.core.logger import get_logger

logger = get_logger("target_db.manager")

class TargetDBConnectionManager:
    """
    Singleton que gerencia o cache de engines SQLAlchemy.
    Evita abrir conexões excessivas no MySQL.
    """
    
    _instance: Optional['TargetDBConnectionManager'] = None
    # Cache: {"agent_id:database_connection_id": engine}
    _engines: Dict[str, Engine] = {}
    # Cache de metadados para detectar mudanças de binding/conexão
    _meta_cache: Dict[str, str] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TargetDBConnectionManager, cls).__new__(cls)
        return cls._instance

    def _cache_key(self, agent_id: str, database_connection_id: int | str) -> str:
        return f"{agent_id}:{database_connection_id}"

    def get_engine(self, db: Session, agent_id: str, database_connection_id: Optional[int] = None) -> Engine:
        """
        Retorna uma engine do cache ou cria uma nova, baseada no binding ativo do agente.

        Aceita `database_connection_id` opcional para resolver um binding específico,
        sempre validando que existe binding ativo para o agente.
        """
        resolved = agent_database_binding_service.resolve_agent_database_binding(
            db,
            agent_id,
            database_connection_id=database_connection_id,
        )

        db_connection_id = resolved.get("database_connection_id")
        if db_connection_id is None:
            cache_connection_key: int | str = f"legacy-{resolved.get('binding_id')}"
        else:
            cache_connection_key = int(db_connection_id)

        cache_key = self._cache_key(agent_id, cache_connection_key)

        # Se a resolução default mudou para outra conexão, descarta engines antigas do mesmo agente.
        for existing_key in list(self._engines.keys()):
            if existing_key.startswith(f"{agent_id}:") and existing_key != cache_key:
                old_engine = self._engines.pop(existing_key, None)
                self._meta_cache.pop(existing_key, None)
                if old_engine is not None:
                    old_engine.dispose()

        current_meta = "|".join(
            [
                str(resolved.get("binding_id")),
                str(resolved.get("binding_updated_at")),
                str(resolved.get("connection_updated_at")),
                str(resolved.get("access_mode")),
            ]
        )

        # Invalidação de cache quando metadados mudam
        if cache_key in self._engines and self._meta_cache.get(cache_key) != current_meta:
            logger.info(
                "Binding/conexão alterado. Recriando engine | agent=%s | db_connection_id=%s",
                agent_id,
                cache_connection_key,
            )
            old_engine = self._engines.pop(cache_key, None)
            if old_engine is not None:
                old_engine.dispose()

        # Cria engine quando não existe em cache
        if cache_key not in self._engines:
            engine = create_target_engine(resolved)
            self._engines[cache_key] = engine
            self._meta_cache[cache_key] = current_meta
            logger.info(
                "Engine de target DB cacheada | agent=%s | db_connection_id=%s",
                agent_id,
                cache_connection_key,
            )

        return self._engines[cache_key]

    def clear(self):
        """Limpa todo o cache de conexões (Shutdown)."""
        for cache_key, engine in self._engines.items():
            engine.dispose()
            logger.info("Engine descartada | cache_key=%s", cache_key)
        self._engines.clear()
        self._meta_cache.clear()

# Instância Singleton exportada
connection_manager = TargetDBConnectionManager()
