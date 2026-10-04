import secrets
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.db_models import Workspace, Document, ChatSession, User
from backend.models.schemas import WorkspaceCreate, RenameRequest
from backend.api.dependencies import Identity, get_identity, authorize_workspace, require_user

router=APIRouter(prefix="/workspaces",tags=["workspaces"])

@router.post("",status_code=201)
def create_workspace(p:WorkspaceCreate,identity:Identity=Depends(get_identity),db:Session=Depends(get_db)):
    guest=identity.guest_id
    if not identity.user and not guest: guest=secrets.token_urlsafe(32)
    w=Workspace(name=p.name,user_id=identity.user.id if identity.user else None,guest_id=None if identity.user else guest)
    db.add(w); db.commit(); db.refresh(w)
    return {"id":str(w.id),"name":w.name,"guest_id":guest if not identity.user else None}

@router.get("")
def list_workspaces(user:User=Depends(require_user),db:Session=Depends(get_db)):
    rows=db.query(Workspace).filter(Workspace.user_id==user.id).order_by(Workspace.created_at.desc()).all()
    return [{"id":str(w.id),"name":w.name,"created_at":w.created_at,"documents":len(w.documents),"chats":len(w.chat_sessions)} for w in rows]

@router.get("/{workspace_id}")
def detail(workspace_id:UUID,identity:Identity=Depends(get_identity),db:Session=Depends(get_db)):
    w=db.get(Workspace,workspace_id)
    if not w: raise HTTPException(404,"Workspace not found")
    authorize_workspace(w,identity)
    return {"id":str(w.id),"name":w.name,
            "documents":[{"id":str(d.id),"filename":d.filename,"status":d.status,"summary":d.summary} for d in w.documents],
            "chats":[{"id":str(c.id),"title":c.title,"created_at":c.created_at} for c in w.chat_sessions]}

@router.patch("/{workspace_id}")
def rename(workspace_id:UUID,p:RenameRequest,identity:Identity=Depends(get_identity),db:Session=Depends(get_db)):
    w=db.get(Workspace,workspace_id)
    if not w: raise HTTPException(404,"Workspace not found")
    authorize_workspace(w,identity); w.name=p.name; db.commit()
    return {"ok":True}

@router.post("/claim-guest")
def claim_guest(x_guest_id:str=Header(...),user:User=Depends(require_user),db:Session=Depends(get_db)):
    n=db.query(Workspace).filter(Workspace.guest_id==x_guest_id).update({"user_id":user.id,"guest_id":None},synchronize_session=False)
    db.commit(); return {"transferred":n}
