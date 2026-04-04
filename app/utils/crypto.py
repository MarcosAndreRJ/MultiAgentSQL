"""
Utilities mínimos para criptografia simétrica de senhas.

Uso:
 - encrypt_secret(plain) -> ciphertext
 - decrypt_secret(ciphertext) -> plain

Implementação deliberadamente simples com Fernet (cryptography) quando
disponível; fallback para rot13-like (inseguro) se lib não existir — isso
permite rodar nos ambientes de desenvolvimento sem dependências extras.

NOTA: Em produção, garanta que uma chave segura é fornecida via APP_SECRET_KEY
ou via um Key Management Service e que a dependência `cryptography` esteja
instalada.
"""
from typing import Optional
import base64
import logging

logger = logging.getLogger("utils.crypto")

_FERNET_AVAILABLE = False
try:
    from cryptography.fernet import Fernet
    _FERNET_AVAILABLE = True
except Exception:
    logger.warning("cryptography.Fernet não disponível — usando fallback inseguro para criptografia local")


def _derive_key(secret: str) -> bytes:
    # Deriva uma chave Fernet a partir de uma string. Simples: usa base64.urlsafe_b64encode
    # do APP_SECRET_KEY. Em produção, usar KMS ou derivação forte.
    b = secret.encode("utf-8")
    key = base64.urlsafe_b64encode(b.ljust(32, b"0")[:32])
    return key


def encrypt_secret(plain: str, master_key: Optional[str] = None) -> str:
    """Retorna ciphertext em base64 string.

    master_key: string usada para derivar chave simétrica. Se não fornecida,
    usa APP_SECRET_KEY via import da settings (se disponível)."""
    from app.core.settings import settings

    mk = master_key or getattr(settings, "APP_SECRET_KEY", None) or "dev-secret-please-change"
    if _FERNET_AVAILABLE:
        f = Fernet(_derive_key(mk))
        token = f.encrypt(plain.encode("utf-8"))
        return token.decode("utf-8")
    # Fallback (inseguro): base64 encode
    logger.debug("Usando fallback de criptografia (base64) — não seguro para produção")
    return base64.b64encode(plain.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str, master_key: Optional[str] = None) -> str:
    from app.core.settings import settings

    mk = master_key or getattr(settings, "APP_SECRET_KEY", None) or "dev-secret-please-change"
    if _FERNET_AVAILABLE:
        f = Fernet(_derive_key(mk))
        return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    # Fallback (inseguro): base64 decode
    try:
        return base64.b64decode(ciphertext.encode("utf-8")).decode("utf-8")
    except Exception:
        logger.error("Falha ao descriptografar secret com fallback base64")
        raise


def mask_password_for_output(value: Optional[str]) -> str:
    if not value:
        return "NOT_SET"
    if len(value) <= 4:
        return "****"
    return f"{value[:2]}...{value[-2:]}"
