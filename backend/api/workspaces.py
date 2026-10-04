from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.db_models import Workspace, User, GuestSession, Dataset
from backend.models.schemas import WorkspaceCreate, RenameRequest
from backend.api.dependencies import Identity, get_identity, require_user
from backend.services.ownership import workspace
from backend.services.authentication import create_guest
from backend.services.rate_limit import limit
from backend.security import token_hash
from backend.config import settings

router=APIRouter(prefix="/workspaces",tags=["workspaces"])

@router.post("",status_code=201)
def create_workspace(p:WorkspaceCreate,request:Request,identity:Identity=Depends(get_identity),db:Session=Depends(get_db)):
    if identity.user and not identity.user.email_verified:
        raise HTTPException(403,"Verify your email before creating a workspace")
    guest=identity.guest_id; secret=None
    if not identity.user and not guest:
        limit(db,"guest-ip",request.client.host if request.client else "unknown",20)
        secret,guest=create_guest(db)
    if guest:
        db.query(GuestSession).filter_by(token_hash=guest).with_for_update().one()
        if db.query(Workspace).filter_by(guest_id=guest).count()>=settings.GUEST_MAX_WORKSPACES:
            raise HTTPException(429,"Guest workspace quota reached")
    row=Workspace(name=p.name,user_id=identity.user.id if identity.user else None,guest_id=None if identity.user else guest)
    db.add(row); db.commit(); db.refresh(row)
    return {"id":str(row.id),"name":row.name,"guest_id":secret}

@router.get("")
def list_workspaces(identity:Identity=Depends(get_identity),db:Session=Depends(get_db)):
    if identity.user:
        if not identity.user.email_verified: raise HTTPException(403,"Verify your email first")
        query=db.query(Workspace).filter_by(user_id=identity.user.id)
    elif identity.guest_id:
        query=db.query(Workspace).filter_by(guest_id=identity.guest_id)
    else:
        raise HTTPException(401,"Authentication required")
    return [{"id":str(w.id),"name":w.name,"created_at":w.created_at,"documents":len(w.documents),
             "chats":len(w.chat_sessions),"datasets":db.query(Dataset).filter_by(workspace_id=w.id).count()}
            for w in query.order_by(Workspace.created_at.desc()).all()]

@router.get("/{workspace_id}")
def detail(workspace_id:UUID,identity:Identity=Depends(get_identity),db:Session=Depends(get_db)):
    w=workspace(db,workspace_id,identity)
    return {"id":str(w.id),"name":w.name,
            "documents":[{"id":str(d.id),"filename":d.filename,"status":d.status,"summary":d.summary,"error":d.error} for d in w.documents],
            "chats":[{"id":str(c.id),"title":c.title,"created_at":c.created_at} for c in w.chat_sessions]}

@router.patch("/{workspace_id}")
def rename(workspace_id:UUID,p:RenameRequest,identity:Identity=Depends(get_identity),db:Session=Depends(get_db)):
    w=workspace(db,workspace_id,identity,lock=True); w.name=p.name; db.commit()
    return {"ok":True}

@router.post("/claim-guest")
def claim_guest(x_guest_id:str=Header(...),user:User=Depends(require_user),db:Session=Depends(get_db)):
    digest=token_hash(x_guest_id.strip())
    guest=db.query(GuestSession).filter_by(token_hash=digest).with_for_update().first()
    if not guest or guest.claimed or guest.expires_at<=datetime.now(timezone.utc):
        raise HTTPException(401,"Guest session is invalid or expired")
    count=db.query(Workspace).filter_by(guest_id=digest).update({"user_id":user.id,"guest_id":None},synchronize_session=False)
    guest.claimed=True; db.commit()
    return {"transferred":count}
