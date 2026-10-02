from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.repositories.doc_repo import delete_document_session
from backend.services.storage import delete_session


router = APIRouter()


@router.delete("/session/{session_id}")
def delete_session_endpoint(
    session_id: str,
    db: Session = Depends(get_db),
):
    try:
        document_id = UUID(session_id)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid session ID",
        ) from exc

    db_deleted = delete_document_session(
        db=db,
        document_id=document_id,
    )

    local_deleted = delete_session(session_id)

    if not db_deleted and not local_deleted:
        raise HTTPException(
            status_code=404,
            detail="Session not found",
        )

    return {
        "status": "deleted",
        "session_id": session_id,
        "database_deleted": db_deleted,
        "local_storage_deleted": local_deleted,
    }