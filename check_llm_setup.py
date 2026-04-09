from app.db.session import engine
from sqlalchemy import text

def check_providers():
    with engine.connect() as conn:
        print("Providers:")
        res = conn.execute(text("SELECT id, name, provider_type FROM llm_providers"))
        for row in res:
            print(f"  ID: {row[0]}, Name: {row[1]}, Type: {row[2]}")
            
        print("\nModels:")
        res = conn.execute(text("SELECT id, provider_id, model_identifier FROM llm_models"))
        for row in res:
            print(f"  ID: {row[0]}, Provider ID: {row[1]}, Identifier: {row[2]}")

if __name__ == "__main__":
    check_providers()
