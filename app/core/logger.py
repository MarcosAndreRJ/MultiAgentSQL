"""
Sistema de logging centralizado para o MultiAgent SQL.
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

from app.core.settings import settings


def setup_logger(name: str = "multiagent-sql") -> logging.Logger:
    """
    Configura e retorna um logger com handlers para console e arquivo.
    """
    logger = logging.getLogger(name)

    # Evitar configurar múltiplas vezes
    if logger.handlers:
        return logger

    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler: console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler: arquivo rotativo
    log_dir = settings.logs_path
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_dir / "multiagent-sql.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# Logger raiz do sistema
logger = setup_logger()


def get_logger(module_name: str) -> logging.Logger:
    """Retorna um logger filho para um módulo específico."""
    return logging.getLogger(f"multiagent-sql.{module_name}")
