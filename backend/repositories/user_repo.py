from uuid import UUID

from sqlalchemy.orm import Session

from backend.models.db_models import User


def normalize_email(email: str) -> str:
    """
    Emails are stored trimmed and lower-cased so that
    'Ann@Example.com' and 'ann@example.com' are the same account.
    """
    return email.strip().lower()


def create_user(
    db: Session,
    email: str,
    password_hash: str,
) -> User:
    user = User(
        email=normalize_email(email),
        password_hash=password_hash,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def get_user_by_email(
    db: Session,
    email: str,
) -> User | None:
    return (
        db.query(User)
        .filter(User.email == normalize_email(email))
        .first()
    )


def get_user_by_id(
    db: Session,
    user_id: UUID,
) -> User | None:
    return (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )
