import os
from fastapi import APIRouter, HTTPException
from backend.utils.cleanup import delete_session_folder
from backend.config import STORAGE_DIR
router = APIRouter()



@router.delete("/session/{session_id}")
def delete_session(session_id: str):
    session_path = os.path.join(STORAGE_DIR, session_id)

    if not os.path.exists(session_path):
        raise HTTPException(status_code=404, detail="Session not found")

    delete_session_folder(session_path)

    return {
        "status": "deleted",
        "session_id": session_id
    }