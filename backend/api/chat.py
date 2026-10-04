import uuid
from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.db_models import Workspace,Document,ChatSession,Message
from backend.models.schemas import ChatRequest
from backend.api.dependencies import Identity,get_identity,authorize_workspace
from backend.services.retrieval import hybrid_search
from backend.services.llm import answer

router=APIRouter(tags=["chat"])

@router.post("/workspaces/{workspace_id}/chats",status_code=201)
def create_chat(workspace_id:UUID,identity:Identity=Depends(get_identity),db:Session=Depends(get_db)):
    w=db.get(Workspace,workspace_id)
    if not w: raise HTTPException(404,"Workspace not found")
    authorize_workspace(w,identity)
    c=ChatSession(workspace_id=w.id); db.add(c); db.commit(); db.refresh(c)
    return {"id":str(c.id),"title":c.title}

@router.get("/chats/{chat_id}/history")
def history(chat_id:UUID,identity:Identity=Depends(get_identity),db:Session=Depends(get_db)):
    c=db.get(ChatSession,chat_id)
    if not c: raise HTTPException(404,"Chat not found")
    authorize_workspace(c.workspace,identity)
    return {"history":[{"role":m.role,"content":m.content,"sources":m.sources or [],"created_at":m.created_at} for m in c.messages]}

@router.post("/chats/{chat_id}/ask")
def ask(chat_id:UUID,p:ChatRequest,identity:Identity=Depends(get_identity),db:Session=Depends(get_db)):
    c=db.get(ChatSession,chat_id)
    if not c: raise HTTPException(404,"Chat not found")
    authorize_workspace(c.workspace,identity)
    allowed={d.id for d in c.workspace.documents if d.status=="indexed"}
    ids=set(allowed if p.document_ids is None else p.document_ids)
    if not ids or not ids.issubset(allowed): raise HTTPException(400,"Invalid document selection")
    recent=c.messages[-8:]
    memory="\n".join(f"{m.role}: {m.content}" for m in recent)
    hits=hybrid_search(db,list(ids),p.query)
    if not hits: raise HTTPException(404,"No relevant document content found")
    context=[]; sources=[]
    for h in hits[:5]:
        ch=h["chunk"]; fn=h["filename"]
        label=f"{fn} | Page {ch.page_number or '-'} | Chunk {ch.chunk_index}"
        context.append(f"[Source: {label}]\n{ch.content}")
        sources.append({"file_name":fn,"document_id":str(ch.document_id),"page_number":ch.page_number,
                        "section_title":ch.section_title,"chunk_index":ch.chunk_index})
    response=answer("\n\n---\n\n".join(context),p.query,memory)
    if c.title=="New chat": c.title=p.query[:80]
    db.add(Message(chat_session_id=c.id,role="user",content=p.query))
    db.add(Message(chat_session_id=c.id,role="assistant",content=response,sources=sources))
    db.commit()
    return {"answer":response,"sources":sources}
