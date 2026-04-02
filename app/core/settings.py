"""
Módulo de configurações centrais da aplicação.
Usa pydantic-settings para carregar variáveis de ambiente e .env.
"""
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações globais do MultiAgent SQL."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_DEBUG: bool = False
    APP_SECRET_KEY: str = "change-me-in-production"

    # ── Ollama ────────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_DEFAULT_MODEL: str = "llama3.1:8b"
    OLLAMA_TIMEOUT: int = 120
    OLLAMA_CLOUD_API_KEY: str = ""

    # ── Gemini ────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL_DEFAULT: str = "gemini-2.0-flash-lite"
    GEMINI_TIMEOUT_SECONDS: int = 30
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"

    # ── Paths ─────────────────────────────────────────────
    AGENTS_CONFIG_DIR: str = "config/agents"
    SKILLS_DIR: str = "config/skills"
    PROMPTS_DIR: str = "config/prompts"
    DATA_DIR: str = "data"

    # ── Guard & Pending Actions ───────────────────────────
    PENDING_ACTION_TTL: int = 300  # seconds

    # ── Session & Memory ──────────────────────────────────
    SESSION_MAX_MESSAGES: int = 20
    SESSION_MAX_SQL_HISTORY: int = 5

    # ── Logging ───────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"

    # ── Database Defaults ─────────────────────────────────
    DB_MAX_RESULT_ROWS: int = 500

    # ── MySQL Connection ─────────────────────────────────
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_DATABASE: str = "MultiAgent"
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "root"

    # ── Derived paths (computed, not env vars) ────────────
    @property
    def agents_config_path(self) -> Path:
        return Path(self.AGENTS_CONFIG_DIR)

    @property
    def skills_path(self) -> Path:
        return Path(self.SKILLS_DIR)

    @property
    def prompts_path(self) -> Path:
        return Path(self.PROMPTS_DIR)

    @property
    def logs_path(self) -> Path:
        return Path(self.LOG_DIR)

    @property
    def data_path(self) -> Path:
        return Path(self.DATA_DIR)

    @property
    def digests_path(self) -> Path:
        return Path(self.DATA_DIR) / "digests"

    @property
    def aliases_path(self) -> Path:
        return Path(self.DATA_DIR) / "aliases"

    @property
    def drafts_path(self) -> Path:
        return Path(self.DATA_DIR) / "diagram_drafts"

    @property
    def analytics_path(self) -> Path:
        return Path(self.DATA_DIR) / "analytics"

    @property
    def cache_path(self) -> Path:
        return Path(self.DATA_DIR) / "cache"

    @property
    def database_url(self) -> str:
        """Retorna a URL de conexão MySQL para o SQLAlchemy."""
        # Suporta mysql-connector-python conforme requirements.txt
        return f"mysql+mysqlconnector://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"


# Instância global de settings
settings = Settings()
