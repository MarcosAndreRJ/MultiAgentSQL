import mysql.connector
import os
import sys
from dotenv import load_dotenv

# Carregar variáveis do .env
load_dotenv()

def test_connection():
    host = os.getenv("MYSQL_HOST", "192.168.0.5")
    port = os.getenv("MYSQL_PORT", "3306")
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "root")
    database = os.getenv("MYSQL_DATABASE", "MultiAgent")

    print(f"--- Diagnóstico de Conexão MySQL ---")
    print(f"Tentando conectar em: {host}:{port}")
    print(f"Usuário: {user}")
    print(f"Banco: {database}")
    print("-" * 35)

    try:
        conn = mysql.connector.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            database=database,
            connect_timeout=5
        )
        print("✅ SUCESSO: Conexão estabelecida com o servidor!")
        
        # Verificação de Esquema
        print("\n--- Verificação de Esquema ---")
        cursor = conn.cursor()
        cursor.execute("SHOW COLUMNS FROM agents LIKE 'icon'")
        if cursor.fetchone():
            print("✅ OK: Coluna 'icon' já existe na tabela 'agents'.")
        else:
            print("⚠️ AVISO: Coluna 'icon' ausente na tabela 'agents'.")
            print("🛠️  SOLUÇÃO (Execute no MySQL):")
            print("   ALTER TABLE agents ADD COLUMN icon VARCHAR(20) DEFAULT '🤖' AFTER agent_type;")
        
        conn.close()
    except mysql.connector.Error as err:
        print(f"❌ ERRO: {err}")
        
        if err.errno == 2003: # Connection Refused / Can't connect
            print("\n💡 POSSÍVEIS CAUSAS (Connection Refused):")
            print(f"1. O MySQL não está rodando no servidor {host}.")
            print(f"2. O firewall do servidor {host} está bloqueando a porta {port}.")
            print(f"3. O MySQL está configurado para aceitar APENAS conexões locais (bind-address = 127.0.0.1).")
            print(f"4. O usuário '{user}' não tem permissão para conectar de Hosts remotos.")
            
            print("\n🛠️  SOLUÇÃO RECOMENDADA (Execute no servidor 192.168.0.5):")
            print("No workbench ou terminal do servidor, execute:")
            print(f"  CREATE USER IF NOT EXISTS '{user}'@'%' IDENTIFIED BY '{password}';")
            print(f"  GRANT ALL PRIVILEGES ON *.* TO '{user}'@'%' WITH GRANT OPTION;")
            print("  FLUSH PRIVILEGES;")
            print("\nE verifique o arquivo my.cnf / my.ini:")
            print("  bind-address = 0.0.0.0")

if __name__ == "__main__":
    test_connection()
