import requests
import json

BASE_URL = "http://localhost:8000"

def check_agent(agent_id):
    print(f"--- Verificando Agente: {agent_id} ---")
    try:
        # Busca detalhes
        url = f"{BASE_URL}/api/agents/{agent_id}"
        print(f"Chamando: {url}")
        res = requests.get(url)
        if res.status_code == 200:
            data = res.json()
            agent = data.get("agent", {})
            db = agent.get("database")
            print(f"Sucesso! Banco retornado: {json.dumps(db, indent=2)}")
        else:
            print(f"ERRO API: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"Erro de conexão: {e}")

if __name__ == "__main__":
    # Vamos testar o dba_devhacks (ou o primeiro agente que encontrar)
    try:
        list_res = requests.get(f"{BASE_URL}/api/agents")
        agents = list_res.json().get("agents", [])
        if agents:
            check_agent(agents[0]["id"])
            # Se tiver o dba_devhacks, testa ele
            devhacks = next((a for a in agents if "devhacks" in a["id"] or "devhacks" in a["name"]), None)
            if devhacks:
                check_agent(devhacks["id"])
        else:
            print("Nenhum agente encontrado na lista.")
    except Exception as e:
        print(f"Falha ao listar agentes: {e}")
