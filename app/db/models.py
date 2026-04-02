"""
Modelos ORM (Tabelas) do Banco de Dados MySQL.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.db.session import Base

class LLMProvider(Base):
    """Tabela de provedores de LLM."""
    __tablename__ = "llm_providers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    provider_type = Column(String(20), nullable=False)  # "ollama", "gemini", "openai"
    base_url = Column(String(255), nullable=True)
    api_key_masked = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    source = Column(String(20), default="live")        # "bootstrap", "live", "manual"
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamento com modelos
    models = relationship("LLMModel", back_populates="provider", cascade="all, delete-orphan")

class LLMModel(Base):
    """Tabela de modelos disponíveis por provedor."""
    __tablename__ = "llm_models"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("llm_providers.id"), nullable=False)
    model_identifier = Column(String(100), nullable=False, index=True) # Nome técnico (ex: llama3)
    display_name = Column(String(100), nullable=False)                 # Nome amigável (ex: Llama 3)
    
    supports_tools = Column(Boolean, default=False)
    supports_json = Column(Boolean, default=False)
    supports_streaming = Column(Boolean, default=True)
    is_available = Column(Boolean, default=True)
    source = Column(String(20), default="sync")        # "sync", "manual"

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamento com o provider
    provider = relationship("LLMProvider", back_populates="models")
