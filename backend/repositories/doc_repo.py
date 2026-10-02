from uuid import UUID

from sqlalchemy.orm import Session

from backend.models.db_models import Document


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