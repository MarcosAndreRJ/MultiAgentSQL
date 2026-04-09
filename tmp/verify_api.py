
import asyncio
from app.api.routes_agents import list_agents
import json

async def verify():
    try:
        response = await list_agents()
        print("API Response Structure:")
        print(json.dumps(response, indent=2, default=str))
        
        if "agents" in response and isinstance(response["agents"], list):
            print(f"\nSUCCESS: API is returning {len(response['agents'])} agents inside 'agents' key.")
        else:
            print("\nFAILURE: API response format is incorrect.")
            
    except Exception as e:
        print(f"Error during verification: {e}")

if __name__ == "__main__":
    asyncio.run(verify())
