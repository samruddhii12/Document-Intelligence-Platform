from uuid import UUID
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Response
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.database import get_db
from backend.models.db_models import Document, Job, ChatSession, Message
from backend.api.dependencies import Identity, get_identity
from backend.services.ownership import resource, upload_quota
from backend.services.content_store import content_store
from backend.services.uploads import read_upload
from backend.services.llm import summarize, suggested_questions

router=APIRouter(tags=["documents"])

@router.post("/workspaces/{workspace_id}/documents",status_code=202)
async def upload(workspace_id:UUID,file:UploadFile=File(...),identity:Identity=Depends(get_identity),db:Session=Depends(get_db)):
    upload_quota(db,workspace_id,identity)
    filename,extension,content=await read_upload(file,{"pdf","docx","md","txt"})
    obj=content_store.put(db,workspace_id,filename,content,file.content_type or "application/octet-stream")
    document=Document(workspace_id=workspace_id,object_id=obj.id,filename=filename,file_type=extension,status="queued")
    db.add(document); db.flush()
    job=Job(workspace_id=workspace_id,resource_id=document.id,kind="document"); db.add(job)
    db.commit(); db.refresh(job)
    return {"id":str(document.id),"filename":filename,"status":document.status,"job_id":str(job.id)}

@router.get("/documents/{document_id}")
def detail(document_id:UUID,identity:Identity=Depends(get_identity),db:Session=Depends(get_db)):
    d=resource(db,Document,document_id,identity)
    return {"id":str(d.id),"filename":d.filename,"status":d.status,"error":d.error,"metadata":d.metadata_json,"version":d.version}

@router.get("/documents/{document_id}/download")
def download(document_id:UUID,identity:Identity=Depends(get_identity),db:Session=Depends(get_db)):
    d=resource(db,Document,document_id,identity)
    if not d.object_id: raise HTTPException(409,"Original content has not been migrated")
    from urllib.parse import quote
    return Response(content_store.read(db,d.object_id,d.workspace_id),media_type="application/octet-stream",
                    headers={"Content-Disposition":"attachment; filename*=UTF-8''"+quote(d.filename),"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"})

@router.post("/documents/{document_id}/retry",status_code=202)
def retry(document_id:UUID,identity:Identity=Depends(get_identity),db:Session=Depends(get_db)):
    d=resource(db,Document,document_id,identity)
    d=db.query(Document).filter_by(id=d.id).with_for_update().one()
    if d.status!="failed" or not d.object_id: raise HTTPException(409,"Only failed persisted documents can be retried")
    d.status="queued"; d.error=None
    db.add(Job(workspace_id=d.workspace_id,resource_id=d.id,kind="document")); db.commit()
    return {"status":"queued"}

def ready(db,document_id,identity):
    d=resource(db,Document,document_id,identity)
    if d.status!="indexed" or not d.chunks: raise HTTPException(409,"Document must be successfully indexed first")
    return d

@router.post("/documents/{document_id}/summary")
def document_summary(document_id:UUID,identity:Identity=Depends(get_identity),db:Session=Depends(get_db)):
    d=ready(db,document_id,identity)
    if d.summary: return {"summary":d.summary}
    version=d.version
    texts=[c.content for c in sorted(d.chunks,key=lambda c:c.chunk_index)]
    db.commit()  # Release read transactions during LLM generation.
    result=summarize("\n".join(texts))
    d=db.query(Document).filter_by(id=document_id).with_for_update().first()
    if not d or d.version!=version: raise HTTPException(409,"Document changed during summarization")
    from backend.api.dependencies import authorize_workspace
    authorize_workspace(d.workspace,identity)
    d.summary=result; db.commit()
    return {"summary":result}

@router.get("/documents/{document_id}/suggested-questions")
def questions(document_id:UUID,identity:Identity=Depends(get_identity),db:Session=Depends(get_db)):
    d=ready(db,document_id,identity)
    text="\n".join(c.content for c in sorted(d.chunks,key=lambda c:c.chunk_index))
    db.commit()
    return {"questions":[x.strip("-• 1234567890.") for x in suggested_questions(text).splitlines() if x.strip()][:5]}

@router.delete("/documents/{document_id}")
def delete(document_id:UUID,identity:Identity=Depends(get_identity),db:Session=Depends(get_db)):
    d=resource(db,Document,document_id,identity)
    d=db.query(Document).filter_by(id=d.id).with_for_update().one()
    object_id,workspace_id=d.object_id,d.workspace_id
    # Remove conversations containing generated answers derived from this source.
    affected=select(Message.chat_session_id).where(Message.sources.contains([{"document_id":str(d.id)}]))
    for chat in db.query(ChatSession).filter(ChatSession.workspace_id==workspace_id,ChatSession.id.in_(affected)).all():
        db.delete(chat)
    db.query(Job).filter_by(resource_id=d.id,workspace_id=workspace_id).delete(synchronize_session=False)
    db.delete(d); db.flush()
    if object_id: content_store.delete(db,object_id,workspace_id)
    db.commit()
    return {"deleted":True}
