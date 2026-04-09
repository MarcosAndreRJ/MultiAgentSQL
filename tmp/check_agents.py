
import asyncio
from app.db.session import SessionLocal
from app.db import models as db_models
import json

async def check_db():
    db = SessionLocal()
    try:
        print("--- Agents in DB ---")
        agents = db.query(db_models.Agent).all()
        if not agents:
            print("No agents found in 'agents' table.")
        for ag in agents:
            print(f"ID: {ag.id} | Name: {ag.name} | Active: {ag.is_active} | Source: {ag.source}")
            
        print("\n--- Agent Database Bindings ---")
        bindings = db.query(db_models.AgentDatabaseBinding).all()
        for b in bindings:
            print(f"ID: {b.id} | AgentID: {b.agent_id} | DB: {b.database_name} | Active: {b.is_active}")

        print("\n--- Agent LLM Bindings ---")
        llm_bindings = db.query(db_models.AgentLLMBinding).all()
        for lb in llm_bindings:
            print(f"ID: {lb.id} | AgentID: {lb.agent_id} | ModelID: {lb.model_id} | Active: {lb.is_active}")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(check_db())
