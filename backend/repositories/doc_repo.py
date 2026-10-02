from uuid import UUID
from sqlalchemy.orm import Session
from backend.models.db_models import Document
from backend.models.db_models import (
    ChatSession,
    Document,
    Workspace,
)


def create_document(
    db: Session,
    document_id: UUID,
    workspace_id: UUID,
    filename: str,
    file_type: str,
    storage_path: str | None = None,
    status: str = "uploaded",
) -> Document:
    document = Document(
        id=document_id,
        workspace_id=workspace_id,
        filename=filename,
        file_type=file_type,
        storage_path=storage_path,
        status=status,
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return document


def get_document(
    db: Session,
    document_id: UUID,
) -> Document | None:
    return (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )


def list_workspace_documents(
    db: Session,
    workspace_id: UUID,
) -> list[Document]:
    return (
        db.query(Document)
        .filter(Document.workspace_id == workspace_id)
        .order_by(Document.created_at.desc())
        .all()
    )


def update_document_status(
    db: Session,
    document_id: UUID,
    status: str,
) -> Document | None:
    document = get_document(db, document_id)

    if document is None:
        return None

    document.status = status

    db.commit()
    db.refresh(document)

    return document



def delete_document_session(
    db: Session,
    document_id: UUID,
) -> bool:
    document = get_document(
        db=db,
        document_id=document_id,
    )

    if document is None:
        return False

    workspace_id = document.workspace_id

    # Delete chat session.
    # messages are removed automatically by ON DELETE CASCADE.
    chat_session = (
        db.query(ChatSession)
        .filter(ChatSession.id == document_id)
        .first()
    )

    if chat_session is not None:
        db.delete(chat_session)

    # Delete document.
    # chunks are removed automatically by ON DELETE CASCADE.
    db.delete(document)

    db.flush()

    # Current architecture creates one workspace per upload.
    # Remove the workspace if nothing remains inside it.
    remaining_documents = (
        db.query(Document)
        .filter(Document.workspace_id == workspace_id)
        .count()
    )

    remaining_chats = (
        db.query(ChatSession)
        .filter(ChatSession.workspace_id == workspace_id)
        .count()
    )

    if remaining_documents == 0 and remaining_chats == 0:
        workspace = (
            db.query(Workspace)
            .filter(Workspace.id == workspace_id)
            .first()
        )

        if workspace is not None:
            db.delete(workspace)

    db.commit()

    return True