"""Import legacy uploads; optional deletion only after read-back checksum verification."""
import argparse
from pathlib import Path
from backend.database import SessionLocal
from backend.config import settings
from backend.models.db_models import Document
from backend.services.content_store import content_store


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--remove-verified-local",action="store_true")
    args=parser.parse_args()
    root=settings.STORAGE_DIR.resolve()
    imported=0; missing=0
    with SessionLocal() as db:
        ids=[row.id for row in db.query(Document).filter(Document.object_id.is_(None)).all()]
        for resource_id in ids:
            row=db.query(Document).filter_by(id=resource_id).with_for_update().one()
            path=Path(row.storage_path).resolve() if row.storage_path else None
            if not path or not path.is_relative_to(root) or not path.is_file():
                missing+=1; db.rollback(); continue
            data=path.read_bytes()
            obj=content_store.put(db,row.workspace_id,row.filename,data)
            row.object_id=obj.id; row.storage_path=None
            object_id,workspace_id=obj.id,row.workspace_id
            db.commit()
            if content_store.read(db,object_id,workspace_id)!=data:
                raise RuntimeError("Imported content failed verification")
            db.commit(); imported+=1
            if args.remove_verified_local: path.unlink()
    print(f"Imported and verified {imported} files; {missing} originals were missing or outside the legacy storage directory.")

if __name__=="__main__": main()
