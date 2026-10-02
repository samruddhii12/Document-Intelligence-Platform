from uuid import UUID

from sqlalchemy.orm import Session

from backend.models.db_models import ChatSession, Message


def create_chat_session(
    db: Session,
    workspace_id: UUID,
) -> ChatSession:
    chat_session = ChatSession(
        workspace_id=workspace_id,
    )

    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)

    return chat_session


def add_message(
    db: Session,
    chat_session_id: UUID,
    role: str,
    content: str,
) -> Message:
    message = Message(
        chat_session_id=chat_session_id,
        role=role,
        content=content,
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return message


def get_messages(
    db: Session,
    chat_session_id: UUID,
) -> list[Message]:
    return (
        db.query(Message)
        .filter(Message.chat_session_id == chat_session_id)
        .order_by(Message.created_at.asc())
        .all()
    )

def get_chat_session(
    db: Session,
    chat_session_id: UUID,
) -> ChatSession | None:
    return (
        db.query(ChatSession)
        .filter(ChatSession.id == chat_session_id)
        .first()
    )


def get_or_create_chat_session(
    db: Session,
    chat_session_id: UUID,
    workspace_id: UUID,
) -> ChatSession:
    existing = get_chat_session(
        db=db,
        chat_session_id=chat_session_id,
    )

    if existing is not None:
        return existing

    chat_session = ChatSession(
        id=chat_session_id,
        workspace_id=workspace_id,
    )

    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)

    return chat_session