import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.models.schemas import UploadResponse

router = APIRouter()

BASE_STORAGE = "backend/storage/sessions"

@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX allowed")

    session_id = str(uuid.uuid4())
    session_path = os.path.join(BASE_STORAGE, session_id)
    os.makedirs(session_path, exist_ok=True)

    file_path = os.path.join(session_path, file.filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    return UploadResponse(session_id=session_id, filename=file.filename)
