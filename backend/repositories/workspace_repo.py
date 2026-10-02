from sqlalchemy.orm import Session

from backend.models.db_models import Workspace


def create_workspace(
    db: Session,
    name: str,
) -> Workspace:
    workspace = Workspace(name=name)

    db.add(workspace)
    db.commit()
    db.refresh(workspace)

    return workspace


def get_workspace(
    db: Session,
    workspace_id,
) -> Workspace | None:
    return (
        db.query(Workspace)
        .filter(Workspace.id == workspace_id)
        .first()
    )


def list_workspaces(
    db: Session,
) -> list[Workspace]:
    return (
        db.query(Workspace)
        .order_by(Workspace.created_at.desc())
        .all()
    )