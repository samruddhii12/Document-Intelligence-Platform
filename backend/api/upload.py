import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.models.schemas import UploadResponse
from backend.config import STORAGE_DIR

router = APIRouter()

# BASE_STORAGE = STORAGE_DIR

@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX allowed")

    session_id = str(uuid.uuid4())
    session_path = os.path.join(STORAGE_DIR, session_id)
    os.makedirs(session_path, exist_ok=True)

    file_path = os.path.join(session_path, file.filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    return UploadResponse(session_id=session_id, filename=file.filename)
