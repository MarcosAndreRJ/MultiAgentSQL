"""
Service: File Upload and Processing
Responsável por salvar, validar e processar arquivos anexados ao chat de forma temporária.
Limitamos extensão, tamanho e caracteres processados por arquivo para segurança do LLM.
"""
import os
import shutil
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import UploadFile, HTTPException

from app.core.logger import get_logger

logger = get_logger("file_service")

# Constantes de Segurança
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB
MAX_CHARS_PER_FILE = 5000
ALLOWED_EXTENSIONS = {".txt", ".md", ".json", ".csv", ".log"}
UPLOAD_DIR = Path("/tmp/multiagentsql_uploads") if os.name != "nt" else Path(os.environ.get("TEMP", "C:/temp")) / "multiagentsql_uploads"

def _get_session_dir(session_id: str) -> Path:
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir

def save_upload(session_id: str, upload_file: UploadFile) -> dict:
    """Valida, salva o arquivo temporário e retorna metadados."""
    ext = Path(upload_file.filename).suffix.lower() if upload_file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Extensão {ext} não permitida. Apenas txt, md, json, csv, log.")
    
    # Validação de tamanho via spooled file ou limitação pós salvamento
    upload_file.file.seek(0, 2)
    file_size = upload_file.file.tell()
    upload_file.file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"O arquivo {upload_file.filename} excede o limite de 2MB.")

    file_id = f"file_{uuid.uuid4().hex[:8]}"
    safe_filename = f"{file_id}_{upload_file.filename}"
    
    session_dir = _get_session_dir(session_id)
    file_path = session_dir / safe_filename
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
    except Exception as e:
        logger.error(f"Erro ao salvar arquivo {upload_file.filename}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao salvar arquivo")
        
    logger.info(f"Arquivo anexado salvo: {file_path}")
    
    return {
        "id": safe_filename,
        "name": upload_file.filename,
        "size": file_size,
        "type": upload_file.content_type
    }

def process_attachments(session_id: str, file_ids: List[str]) -> Optional[str]:
    """Lê, extrai, e opcionalmente deleta os anexos da sessão convertendo num bloco Markdown formatado."""
    if not file_ids:
        return None
        
    session_dir = _get_session_dir(session_id)
    blocks = []
    
    for fid in file_ids:
        # Prevent traversal
        fid_safe = Path(fid).name
        fpath = session_dir / fid_safe
        
        if not fpath.exists():
            logger.warning(f"Anexo não encontrado para injeção: {fpath}")
            continue
            
        try:
            # Lendo como texto com ignore de erros parciais UTF8 em logs/etc
            content = fpath.read_text(encoding="utf-8", errors="replace")
            
            # Trunca
            if len(content) > MAX_CHARS_PER_FILE:
                content = content[:MAX_CHARS_PER_FILE] + "\n...(arquivo truncado por limite de contexto)"
            
            # Monta bloco
            parts = str(fid_safe).split("_", 2)
            original_name = parts[2] if len(parts) >= 3 else fid_safe
            
            blocks.append(f"[ARQUIVO: {original_name}]\n```\n{content}\n```\n")
            
            # Limpeza opcional após processamento 
            fpath.unlink(missing_ok=True)
            
        except Exception as e:
            logger.error(f"Erro ao ler anexo {fpath}: {e}")
            
    if not blocks:
        return None
        
    return "\n\n".join(blocks)
