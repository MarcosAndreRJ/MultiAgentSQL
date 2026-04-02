"""
API Routes: Chat Upload
POST /api/chat/upload - Envia os anexos multipart
"""
from typing import List

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.services import file_service
from app.core.logger import get_logger

logger = get_logger("routes_upload")
router = APIRouter(prefix="/api/chat", tags=["chat_upload"])

@router.post("/upload")
async def upload_files(
    session_id: str = Form(..., description="ID da sessão do chat"),
    files: List[UploadFile] = File(..., description="Arquivos para anexar")
):
    """
    Recebe list de arquivos e armazena em cache/tmp directory da session, 
    retornando as referências para futuro envio da mensagem.
    """
    if not files:
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado")
        
    metadata = []
    for f in files:
        meta = file_service.save_upload(session_id, f)
        metadata.append(meta)
        
    return metadata
