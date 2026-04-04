-- Migration: observability tables for real execution (Etapa 9.2)

CREATE TABLE IF NOT EXISTS agent_execution_logs (
  id INTEGER PRIMARY KEY AUTO_INCREMENT,
  execution_id VARCHAR(64) NOT NULL,
  agent_id VARCHAR(100) NOT NULL,
  provider_id INTEGER NULL,
  model_id INTEGER NULL,
  database_connection_id INTEGER NULL,
  `query` TEXT NOT NULL,
  status VARCHAR(20) NOT NULL,
  execution_time_ms INTEGER NULL,
  error_message TEXT NULL,
  result_summary_json TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_agent_exec_execution_id (execution_id),
  INDEX idx_agent_exec_agent_id (agent_id),
  INDEX idx_agent_exec_status (status),
  INDEX idx_agent_exec_created_at (created_at),
  INDEX idx_agent_exec_provider_id (provider_id),
  INDEX idx_agent_exec_model_id (model_id),
  INDEX idx_agent_exec_db_conn_id (database_connection_id),
  CONSTRAINT fk_agent_exec_provider FOREIGN KEY (provider_id) REFERENCES llm_providers(id) ON DELETE SET NULL,
  CONSTRAINT fk_agent_exec_model FOREIGN KEY (model_id) REFERENCES llm_models(id) ON DELETE SET NULL,
  CONSTRAINT fk_agent_exec_db_conn FOREIGN KEY (database_connection_id) REFERENCES database_connections(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS provider_execution_logs (
  id INTEGER PRIMARY KEY AUTO_INCREMENT,
  execution_id VARCHAR(64) NOT NULL,
  provider_id INTEGER NULL,
  model_id INTEGER NULL,
  operation VARCHAR(50) NOT NULL,
  status VARCHAR(20) NOT NULL,
  latency_ms INTEGER NULL,
  error_message TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_provider_exec_execution_id (execution_id),
  INDEX idx_provider_exec_provider_id (provider_id),
  INDEX idx_provider_exec_model_id (model_id),
  INDEX idx_provider_exec_status (status),
  INDEX idx_provider_exec_created_at (created_at),
  CONSTRAINT fk_provider_exec_provider FOREIGN KEY (provider_id) REFERENCES llm_providers(id) ON DELETE SET NULL,
  CONSTRAINT fk_provider_exec_model FOREIGN KEY (model_id) REFERENCES llm_models(id) ON DELETE SET NULL
);

ALTER TABLE health_check_logs
  ADD COLUMN execution_id VARCHAR(64) NULL,
  ADD INDEX idx_health_logs_execution_id (execution_id);
