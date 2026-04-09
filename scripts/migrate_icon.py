import mysql.connector
import os
from dotenv import load_dotenv

# Carregar variáveis do .env
load_dotenv()

def migrate():
    host = os.getenv("MYSQL_HOST", "192.168.0.5")
    port = os.getenv("MYSQL_PORT", "3306")
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "root")
    database = os.getenv("MYSQL_DATABASE", "MultiAgent")

    print(f"Executando migração no servidor: {host}:{port}")

    try:
        conn = mysql.connector.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            database=database
        )
        cursor = conn.cursor()
        
        # 1. Verificar se a coluna já existe (Double check)
        cursor.execute("SHOW COLUMNS FROM agents LIKE 'icon'")
        if cursor.fetchone():
            print("✅ A coluna 'icon' já existe!")
        else:
            print("🚀 Adicionando coluna 'icon' à tabela 'agents'...")
            cursor.execute("ALTER TABLE agents ADD COLUMN icon VARCHAR(20) DEFAULT '🤖' AFTER agent_type")
            conn.commit()
            print("✅ Sucesso: Coluna 'icon' adicionada.")
            
        conn.close()
    except Exception as e:
        print(f"❌ Erro na migração: {e}")

if __name__ == "__main__":
    migrate()
