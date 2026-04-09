
import asyncio
from app.db.session import SessionLocal
from app.db import models as db_models

async def check_models():
    db = SessionLocal()
    try:
        print("--- LLM Models in DB ---")
        models = db.query(db_models.LLMModel).all()
        for m in models:
            print(f"ID: {m.id} | Identifier: {m.model_identifier} | Name: {m.display_name}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(check_models())
