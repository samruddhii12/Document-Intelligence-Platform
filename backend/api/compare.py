from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.db_models import Workspace
from backend.api.dependencies import Identity,get_identity,authorize_workspace
from backend.services.llm import generate

router=APIRouter(tags=["intelligence"])

@router.post("/workspaces/{workspace_id}/compare")
def compare(workspace_id:UUID,document_ids:list[UUID],identity:Identity=Depends(get_identity),db:Session=Depends(get_db)):
    w=db.get(Workspace,workspace_id)
    if not w: raise HTTPException(404,"Workspace not found")
    authorize_workspace(w,identity)
    selected=set(document_ids)
    docs=[d for d in w.documents if d.id in selected]
    if len(selected)<2 or len(docs)!=len(selected): raise HTTPException(400,"Select at least two valid workspace documents")
    if any(d.status!="indexed" or not d.chunks for d in docs): raise HTTPException(400,"All selected documents must be successfully indexed first")
    material="\n\n".join(f"DOCUMENT: {d.filename}\n"+"\n".join(c.content for c in d.chunks)[:12000] for d in docs)
    result=generate("Compare these documents using only their contents. Identify agreements, differences, conflicts and notable facts.\n\n"+material)
    return {"comparison":result}
