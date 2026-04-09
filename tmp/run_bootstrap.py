
import asyncio
from app.db.session import SessionLocal
from app.services.platform.agent_governance_service import bootstrap_governance_from_yaml
from app.core import agent_registry

async def run_sync():
    # Carregar agentes do YAML primeiro
    agent_registry.load_agents()
    
    db = SessionLocal()
    try:
        print("Iniciando sincronização de governança...")
        stats = bootstrap_governance_from_yaml(db)
        print(f"Sincronização concluída: {stats}")
    except Exception as e:
        print(f"Erro na sincronização: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_sync())
