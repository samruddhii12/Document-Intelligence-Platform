import uuid
from uuid import UUID
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from backend.config import settings
from backend.database import get_db
from backend.models.db_models import Workspace, Document, Chunk
from backend.api.dependencies import Identity,get_identity,authorize_workspace
from backend.services.storage import save_file,delete_document_files
from backend.services.text_extractor import extract_segments
from backend.services.chunker import chunk_segments
from backend.services.embeddings import embed_texts
from backend.services.llm import summarize,suggested_questions

router=APIRouter(tags=["documents"])

def owned_workspace(db,wid,identity):
    w=db.get(Workspace,wid)
    if not w: raise HTTPException(404,"Workspace not found")
    authorize_workspace(w,identity); return w

@router.post("/workspaces/{workspace_id}/documents",status_code=201)
async def upload(workspace_id:UUID,file:UploadFile=File(...),identity:Identity=Depends(get_identity),db:Session=Depends(get_db)):
    w=owned_workspace(db,workspace_id,identity)
    if not file.filename or not file.filename.lower().endswith((".pdf",".docx")): raise HTTPException(400,"Only PDF/DOCX supported")
    content=await file.read()
    if len(content)>settings.MAX_UPLOAD_MB*1024*1024: raise HTTPException(413,"File too large")
    if not content: raise HTTPException(400,"The uploaded file is empty")
    did=uuid.uuid4(); path=save_file(w.id,did,file.filename,content)
    d=Document(id=did,workspace_id=w.id,filename=file.filename,file_type=file.filename.rsplit(".",1)[-1].lower(),storage_path=str(path),status="processing")
    db.add(d); db.commit()
    try:
        try:
            chunks=chunk_segments(extract_segments(str(path)))
        except Exception as error:
            raise HTTPException(400,"Could not read this PDF/DOCX. Upload a valid, unencrypted document.") from error
        if not chunks:
            raise HTTPException(400,"No readable text found. Scanned documents require OCR.")
        vecs=embed_texts([x["content"] for x in chunks])
        db.add_all([Chunk(document_id=d.id,chunk_index=x["chunk_index"],page_number=x["page_number"],
                          section_title=x["section_title"],content=x["content"],embedding=v.tolist()) for x,v in zip(chunks,vecs)])
        d.status="indexed"; db.commit()
    except Exception:
        db.rollback()
        d=db.get(Document,did)
        d.status="failed"; db.commit(); raise
    return {"id":str(d.id),"filename":d.filename,"status":d.status}

@router.post("/documents/{document_id}/summary")
def document_summary(document_id:UUID,identity:Identity=Depends(get_identity),db:Session=Depends(get_db)):
    d=db.get(Document,document_id)
    if not d: raise HTTPException(404,"Document not found")
    authorize_workspace(d.workspace,identity)
    if d.status!="indexed" or not d.chunks: raise HTTPException(400,"Document must be successfully indexed first")
    text="\n".join(c.content for c in d.chunks)
    d.summary=summarize(text); db.commit()
    return {"summary":d.summary}

@router.get("/documents/{document_id}/suggested-questions")
def questions(document_id:UUID,identity:Identity=Depends(get_identity),db:Session=Depends(get_db)):
    d=db.get(Document,document_id)
    if not d: raise HTTPException(404,"Document not found")
    authorize_workspace(d.workspace,identity)
    if d.status!="indexed" or not d.chunks: raise HTTPException(400,"Document must be successfully indexed first")
    text="\n".join(c.content for c in d.chunks)
    return {"questions":[x.strip("-• 1234567890.") for x in suggested_questions(text).splitlines() if x.strip()][:5]}

@router.delete("/documents/{document_id}")
def delete(document_id:UUID,identity:Identity=Depends(get_identity),db:Session=Depends(get_db)):
    d=db.get(Document,document_id)
    if not d: raise HTTPException(404,"Document not found")
    authorize_workspace(d.workspace,identity)
    wid=d.workspace_id; delete_document_files(wid,d.id); db.delete(d); db.commit()
    return {"deleted":True}
