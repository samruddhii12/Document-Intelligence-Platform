from fastapi import HTTPException
from datetime import datetime,timezone
from sqlalchemy import select
from backend.models.db_models import Workspace, Document, Dataset, StoredObject, GuestSession
from backend.api.dependencies import authorize_workspace
from backend.config import settings


def workspace(db, workspace_id, identity, lock=False):
    query=select(Workspace).where(Workspace.id==workspace_id)
    if lock:
        query=query.with_for_update()
    row=db.scalar(query)
    if not row:
        raise HTTPException(404,"Workspace not found")
    authorize_workspace(row,identity)
    return row


def resource(db, model, resource_id, identity):
    row=db.get(model,resource_id)
    if not row:
        raise HTTPException(404,"Resource not found")
    workspace(db,row.workspace_id,identity)
    return row


def upload_quota(db, workspace_id, identity):
    # Lock the shared parent so simultaneous document/dataset uploads cannot exceed quota.
    if identity.guest_id:
        guest=db.query(GuestSession).filter_by(token_hash=identity.guest_id).populate_existing().with_for_update().first()
        if not guest or guest.claimed or guest.expires_at<=datetime.now(timezone.utc): raise HTTPException(401,"Guest session expired")
    w=workspace(db,workspace_id,identity,lock=True)
    if identity.guest_id:
        ids=select(Workspace.id).where(Workspace.guest_id==identity.guest_id)
        count=db.query(StoredObject).filter(StoredObject.workspace_id.in_(ids)).count()
        limit=settings.GUEST_MAX_UPLOADS
    else:
        count=db.query(StoredObject).filter(StoredObject.workspace_id==w.id).count()
        limit=settings.WORKSPACE_MAX_UPLOADS
    if count>=limit:
        raise HTTPException(429,"Upload quota reached")
    return w
