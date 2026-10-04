"""Durable uploads. All methods receive an already-authorized workspace."""
import hashlib
from pathlib import PurePath
from fastapi import HTTPException
from backend.models.db_models import StoredObject, ObjectPayload


class PostgresContentStore:
    def put(self, db, workspace_id, filename, content, media_type="application/octet-stream"):
        obj=StoredObject(workspace_id=workspace_id, filename=PurePath(filename.replace("\\", "/")).name[:500],
                         media_type=media_type[:100], size=len(content), checksum=hashlib.sha256(content).hexdigest())
        obj.payload=ObjectPayload(content=content)
        db.add(obj)
        db.flush()
        return obj

    def read(self, db, object_id, workspace_id):
        obj=db.get(StoredObject, object_id)
        if not obj or obj.workspace_id != workspace_id:
            raise HTTPException(404,"Stored content not found")
        if not obj.payload:
            raise HTTPException(409,"Stored content is missing")
        data=obj.payload.content
        if hashlib.sha256(data).hexdigest() != obj.checksum:
            raise HTTPException(409,"Stored content failed its integrity check")
        return data

    def delete(self, db, object_id, workspace_id):
        obj=db.get(StoredObject, object_id)
        if obj and obj.workspace_id == workspace_id:
            db.delete(obj)


content_store=PostgresContentStore()
