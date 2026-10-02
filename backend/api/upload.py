import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.schemas import UploadResponse
from backend.repositories.doc_repo import create_document
from backend.repositories.workspace_repo import create_workspace
from backend.services.storage import save_document


router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required",
        )

    if not file.filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX allowed",
        )

    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty",
        )

    document_id = uuid.uuid4()
    session_id = str(document_id)

    try:
        file_path = save_document(
            session_id=session_id,
            filename=file.filename,
            content=content,
        )

        workspace = create_workspace(
            db=db,
            name=f"Workspace - {file.filename}",
        )

        file_type = file.filename.rsplit(".", 1)[-1].lower()

        create_document(
            db=db,
            document_id=document_id,
            workspace_id=workspace.id,
            filename=file.filename,
            file_type=file_type,
            storage_path=str(file_path),
            status="uploaded",
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to save uploaded document",
        ) from exc

    return UploadResponse(
        session_id=session_id,
        filename=file.filename,
    )