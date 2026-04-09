
import asyncio
from app.services import agent_service
import json

async def test_list():
    try:
        agents = await agent_service.list_agents()
        print(f"Total agents listed: {len(agents)}")
        for a in agents:
            print(f" - {a.id}: {a.name} (Model: {a.model})")
    except Exception as e:
        print(f"Error listing agents: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_list())
