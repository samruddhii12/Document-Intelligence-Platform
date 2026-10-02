from fastapi import APIRouter, HTTPException

from backend.services.storage import delete_session


router = APIRouter()


@router.delete("/session/{session_id}")
def delete_session_endpoint(session_id: str):
    deleted = delete_session(session_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Session not found",
        )

    return {
        "status": "deleted",
        "session_id": session_id,
    }