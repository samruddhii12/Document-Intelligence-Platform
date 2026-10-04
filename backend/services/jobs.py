"""Durable processing; claim and publish in short transactions around external work."""
import logging
import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy import or_, and_
from fastapi import HTTPException
from backend.models.db_models import Job, Document, Chunk, Dataset, GuestSession, Workspace
from backend.config import settings
from backend.services.content_store import content_store

logger=logging.getLogger(__name__)

def enqueue_claim(db):
    now=datetime.now(timezone.utc)
    job=db.query(Job).filter(or_(Job.status=="queued",and_(Job.status=="processing",Job.lease_until<now)))\
        .order_by(Job.created_at).with_for_update(skip_locked=True).first()
    if not job: db.rollback(); return None
    job.status="processing"; job.attempts+=1; job.lease_token=secrets.token_hex(16)
    job.lease_until=now+timedelta(seconds=settings.JOB_LEASE_SECONDS)
    result=(job.id,job.lease_token)
    db.commit()
    return result

def process(db,job_id,lease_token):
    job=db.get(Job,job_id)
    if not job or job.status!="processing" or job.lease_token!=lease_token: return
    model=Document if job.kind=="document" else Dataset
    row=db.get(model,job.resource_id)
    if not row:
        job.status="cancelled"; db.commit(); return
    owner=db.get(Workspace,row.workspace_id)
    if owner.guest_id:
        guest=db.get(GuestSession,owner.guest_id)
        if not guest or guest.claimed or guest.expires_at<=datetime.now(timezone.utc):
            row.status="failed"; row.error="Guest session expired"; job.status="cancelled"; db.commit(); return
    resource_id,workspace_id,version=row.id,row.workspace_id,row.version
    row.status="processing"
    try:
        content=content_store.read(db,row.object_id,workspace_id)
    except (LookupError,ValueError,HTTPException):
        row.status="failed"; row.error="Stored content is missing or failed its integrity check"
        job.status="failed"; job.error=row.error; db.commit(); return
    extension=row.file_type if job.kind=="document" else row.filename.rsplit(".",1)[-1].lower()
    kind=job.kind
    db.commit()
    try:
        if kind=="document":
            from backend.services.text_extractor import extract_segments, EXTRACTOR_VERSION
            from backend.services.chunker import chunk_segments, CHUNKER_VERSION
            from backend.services.embeddings import embed_texts, model as embedding_model
            segments=extract_segments(content,extension)
            if not segments: raise ValueError("No readable text found. Scanned documents require OCR.")
            # Token counts are taken from the exact embedding tokenizer.
            chunks=chunk_segments(segments,tokenizer=embedding_model().tokenizer)
            if len(chunks)>5000: raise ValueError("Document exceeds the 5000 chunk limit")
            vectors=embed_texts([chunk["content"] for chunk in chunks])
            metadata={"extractor":EXTRACTOR_VERSION,"chunker":CHUNKER_VERSION,"embedding_model":settings.EMBEDDING_MODEL,"chunk_count":len(chunks)}
        else:
            from backend.services.analysis import parse_dataset, profile_dataset, serialize_tables
            tables=parse_dataset(content,extension)
            profile=profile_dataset(tables)
            normalized=serialize_tables(tables)
        db.expire_all()
        # Same locking order as deletion: resource, then job.
        row=db.query(model).filter_by(id=resource_id).with_for_update().first()
        job=db.query(Job).filter_by(id=job_id).with_for_update().first()
        if not row or not job or job.lease_token!=lease_token or job.status!="processing" or row.version!=version:
            db.rollback(); return
        owner=db.get(Workspace,workspace_id)
        if owner.guest_id:
            guest=db.get(GuestSession,owner.guest_id)
            if not guest or guest.expires_at<=datetime.now(timezone.utc): raise ValueError("Guest session expired")
        if kind=="document":
            db.query(Chunk).filter_by(document_id=resource_id).delete(synchronize_session=False)
            for chunk,vector in zip(chunks,vectors):
                db.add(Chunk(document_id=resource_id,chunk_index=chunk["chunk_index"],page_number=chunk["page_number"],
                             section_title=chunk["section_title"],location=chunk.get("location"),content=chunk["content"],embedding=vector.tolist()))
            row.status="indexed"; row.metadata_json=metadata
        else:
            row.profile=profile; row.normalized=normalized; row.status="ready"
        row.error=None; job.status="completed"; job.lease_until=None; job.error=None
        db.commit()
    except Exception as error:
        db.rollback(); logger.exception("Processing job %s failed",job_id)
        row=db.query(model).filter_by(id=resource_id).with_for_update().first()
        job=db.query(Job).filter_by(id=job_id).with_for_update().first()
        if job and job.lease_token==lease_token:
            message=str(error.detail) if isinstance(error,HTTPException) else (str(error) if isinstance(error,(ValueError,UnicodeError)) else "Processing failed. Check worker logs or retry.")
            transient=isinstance(error,HTTPException) and error.status_code>=500
            job.status="queued" if transient and job.attempts<3 else "failed"
            job.error=message[:1000]; job.lease_until=None
            if row: row.status="queued" if job.status=="queued" else "failed"; row.error=job.error
            db.commit()
        else: db.rollback()
