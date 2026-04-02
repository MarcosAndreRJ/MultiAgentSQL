"""
Serviço de Configuração do Dashboard.
Exibe configurações do sistema mas mascarando dados sensíveis.
"""
from typing import Dict
from app.core.settings import settings

def get_masked_config() -> Dict:
    """
    Retorna um subset de settings.py formatado para o dashboard.
    Dados sensíveis como API_KEY e Senhas do banco são mascarados.
    """
    def mask(value: str) -> str:
        if not value: return "NOT_SET"
        if len(value) <= 8: return "********"
        return f"{value[:4]}...{value[-4:]}"

    return {
        "app": {
            "host": settings.APP_HOST,
            "port": settings.APP_PORT,
            "debug": settings.APP_DEBUG,
        },
        "providers": {
            "ollama_url": settings.OLLAMA_BASE_URL,
            "ollama_default": settings.OLLAMA_DEFAULT_MODEL,
            "gemini_model": settings.GEMINI_MODEL_DEFAULT,
            "gemini_key": mask(settings.GEMINI_API_KEY) if settings.GEMINI_API_KEY else "NOT_SET",
        },
        "database": {
            "host": settings.MYSQL_HOST,
            "port": settings.MYSQL_PORT,
            "name": settings.MYSQL_DATABASE,
            "user": settings.MYSQL_USER,
            "password": mask(settings.MYSQL_PASSWORD),
        },
        "paths": {
            "agents": settings.AGENTS_CONFIG_DIR,
            "skills": settings.SKILLS_DIR,
            "prompts": settings.PROMPTS_DIR,
        }
    }
