import uuid

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.schemas import UploadResponse
from backend.repositories.doc_repo import create_document
from backend.repositories.workspace_repo import (
    create_workspace,
    generate_guest_id,
    guest_exists,
)
from backend.services.storage import delete_session, save_document


router = APIRouter()

MAX_GUEST_ID_LENGTH = 64


def resolve_guest_id(
    db: Session,
    supplied_guest_id: str | None,
) -> str:
    """
    TRANSITIONAL (until Phase 3.6 / 3.7 introduce get_current_user()).

    Every workspace needs an owner. Until login exists, each upload is
    owned by a guest identity:

    - If the client sent an X-Guest-Id that THIS server previously
      issued, reuse it.
    - Otherwise mint a new unguessable guest ID. Client-chosen IDs
      that were never issued are ignored, so a guest identity can't
      be pre-claimed or guessed into.
    """
    if supplied_guest_id:
        candidate = supplied_guest_id.strip()

        if (
            0 < len(candidate) <= MAX_GUEST_ID_LENGTH
            and guest_exists(db, candidate)
        ):
            return candidate

    return generate_guest_id()


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    x_guest_id: str | None = Header(default=None),
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

    guest_id = resolve_guest_id(db, x_guest_id)

    try:
        file_path = save_document(
            session_id=session_id,
            filename=file.filename,
            content=content,
        )

        workspace = create_workspace(
            db=db,
            name=f"Workspace - {file.filename}",
            guest_id=guest_id,
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
        # Don't leave a half-created session folder behind.
        delete_session(session_id)

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        delete_session(session_id)

        raise HTTPException(
            status_code=500,
            detail="Failed to save uploaded document",
        ) from exc

    return UploadResponse(
        session_id=session_id,
        filename=file.filename,
        guest_id=guest_id,
    )
