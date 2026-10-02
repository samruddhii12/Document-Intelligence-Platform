import json
import shutil
from pathlib import Path
from typing import Any

from backend.config import STORAGE_DIR


SUPPORTED_DOCUMENT_TYPES = {".pdf", ".docx"}


def get_session_path(session_id: str) -> Path:
    """
    Return the filesystem path for a session.
    """
    return Path(STORAGE_DIR) / session_id


def session_exists(session_id: str) -> bool:
    """
    Check whether a session exists.
    """
    return get_session_path(session_id).exists()


def create_session(session_id: str) -> Path:
    """
    Create the directory for a new session.
    """
    session_path = get_session_path(session_id)
    session_path.mkdir(parents=True, exist_ok=True)
    return session_path


def save_document(
    session_id: str,
    filename: str,
    content: bytes,
) -> Path:
    """
    Save an uploaded PDF or DOCX inside the session.

    Path(filename).name prevents directory traversal such as:
    ../../secret.txt
    """
    session_path = create_session(session_id)

    safe_filename = Path(filename).name
    suffix = Path(safe_filename).suffix.lower()

    if suffix not in SUPPORTED_DOCUMENT_TYPES:
        raise ValueError("Only PDF and DOCX files are supported")

    file_path = session_path / safe_filename
    file_path.write_bytes(content)

    return file_path


def get_document_path(session_id: str) -> Path:
    """
    Locate the uploaded source document for a session.

    We explicitly search for PDF/DOCX instead of relying on
    os.listdir(...)[0].
    """
    session_path = get_session_path(session_id)

    if not session_path.exists():
        raise FileNotFoundError("Session not found")

    documents = [
        path
        for path in session_path.iterdir()
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_DOCUMENT_TYPES
    ]

    if not documents:
        raise FileNotFoundError("No document found")

    if len(documents) > 1:
        raise RuntimeError(
            "Multiple source documents found in a single-document session"
        )

    return documents[0]


def get_index_path(session_id: str) -> Path:
    """
    Return the FAISS index path for a session.
    """
    return get_session_path(session_id) / "faiss.index"


def index_exists(session_id: str) -> bool:
    """
    Check whether a FAISS index exists.
    """
    return get_index_path(session_id).exists()


def save_chunks(session_id: str, chunks: list[str]) -> None:
    """
    Persist document chunks.
    """
    path = get_session_path(session_id) / "chunks.json"

    with path.open("w", encoding="utf-8") as file:
        json.dump(
            chunks,
            file,
            ensure_ascii=False,
            indent=2,
        )


def load_chunks(session_id: str) -> list[str]:
    """
    Load document chunks.
    """
    path = get_session_path(session_id) / "chunks.json"

    if not path.exists():
        raise FileNotFoundError("Chunks not found")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_history_path(session_id: str) -> Path:
    """
    Return the chat history path.
    """
    return get_session_path(session_id) / "history.json"


def load_history(session_id: str) -> list[dict[str, Any]]:
    """
    Load chat history.

    New sessions simply return an empty history.
    """
    path = get_history_path(session_id)

    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_history(
    session_id: str,
    history: list[dict[str, Any]],
) -> None:
    """
    Persist chat history.
    """
    path = get_history_path(session_id)

    with path.open("w", encoding="utf-8") as file:
        json.dump(
            history,
            file,
            ensure_ascii=False,
            indent=2,
        )


def delete_session(session_id: str) -> bool:
    """
    Delete the entire session and all associated files.
    """
    session_path = get_session_path(session_id)

    if not session_path.exists():
        return False

    shutil.rmtree(session_path)

    return True