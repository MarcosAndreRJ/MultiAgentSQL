import sys
import os
from pathlib import Path

# Adiciona a raiz do projeto ao path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.db.session import SessionLocal, engine
from app.db import models
from app.utils.crypto import encrypt_secret
from sqlalchemy import text

def run_migration():
    print("Iniciando migração de AgentDatabaseBinding (V1) para V2...")
    db = SessionLocal()
    
    try:
        # Pega todos os registros da V1
        # Usamos uma raw query caso o model já tenha sido retirado ou para ser mais seguro
        result = db.execute(text("SELECT id, agent_id, db_type, host, port, database_name, username, password, is_default, connection_label, is_active FROM agent_database_bindings"))
        bindings_v1 = result.fetchall()
        
        if not bindings_v1:
            print("Nenhum dado encontrado na V1 ou tabela já vazia.")
        else:
            print(f"Total de {len(bindings_v1)} registros encontrados na V1.")

        count_migrated = 0
        
        for v1 in bindings_v1:
            agent_id = v1.agent_id
            
            # Verifica se já existe ligação V2 para esse agente com a mesma database_name
            # Para evitar dor de cabeça, faremos uma ligação nova apenas se V2 estiver vazio.
            v2_exist = db.query(models.AgentDatabaseBindingV2).filter(
                models.AgentDatabaseBindingV2.agent_id == agent_id
            ).first()
            
            if v2_exist:
                print(f"Agente {agent_id} já possui binding V2. Ignorando migração.")
                continue
                
            # Cria DatabaseConnection
            # Criptografa a senha
            enc_pass = encrypt_secret(v1.password or "")
            
            db_conn = models.DatabaseConnection(
                name=v1.connection_label or f"Conn {agent_id}",
                db_type=v1.db_type or "mysql",
                host=v1.host,
                port=v1.port or 3306,
                database_name=v1.database_name,
                username=v1.username,
                password_encrypted=enc_pass,
                is_active=True
            )
            
            db.add(db_conn)
            db.flush() # Para pegar o ID do db_conn gerado
            
            # Cria o Binding V2
            bind_v2 = models.AgentDatabaseBindingV2(
                agent_id=agent_id,
                database_connection_id=db_conn.id,
                is_default=v1.is_default or False,
                is_primary=v1.is_active or True, # Pela governaça nova
                access_mode="readwrite",
                is_active=v1.is_active or True
            )
            
            db.add(bind_v2)
            count_migrated += 1
            print(f"Migrado agente {agent_id} -> DatabaseConnection ID {db_conn.id}")
        
        db.commit()
        print(f"Migração concluída! Foram migrados {count_migrated} registros.")
        
        # Eliminar a tabela velha com segurança
        try:
            print("Efetuando DROP da tabela legada `agent_database_bindings`...")
            db.execute(text("DROP TABLE IF EXISTS agent_database_bindings"))
            db.commit()
            print("Tabela `agent_database_bindings` deletada com sucesso.")
        except Exception as drop_err:
            print(f"AVISO: não foi possível dropar a tabela legada (talvez locks / constraints): {drop_err}")

    except Exception as e:
        db.rollback()
        print(f"Erro fatal durante a migração: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
