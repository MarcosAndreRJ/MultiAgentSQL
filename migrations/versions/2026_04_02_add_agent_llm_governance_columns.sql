-- Migration: add governance columns to agent_llm_bindings for Etapa 6
-- Safe, non-destructive: new columns are nullable or have defaults

ALTER TABLE agent_llm_bindings
  ADD COLUMN fallback_provider_id INTEGER NULL,
  ADD COLUMN fallback_model_id INTEGER NULL,
  ADD COLUMN require_streaming BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN min_context_window INTEGER NULL,
  ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;

-- Add foreign keys (set null on delete to avoid accidental cascade)
ALTER TABLE agent_llm_bindings
  ADD CONSTRAINT fk_agent_llm_bindings_fallback_provider FOREIGN KEY (fallback_provider_id) REFERENCES llm_providers(id) ON DELETE SET NULL;

ALTER TABLE agent_llm_bindings
  ADD CONSTRAINT fk_agent_llm_bindings_fallback_model FOREIGN KEY (fallback_model_id) REFERENCES llm_models(id) ON DELETE SET NULL;

-- Optional: index the new columns for lookup
CREATE INDEX idx_agent_llm_bindings_fallback_provider ON agent_llm_bindings(fallback_provider_id);
CREATE INDEX idx_agent_llm_bindings_fallback_model ON agent_llm_bindings(fallback_model_id);

-- End of migration
