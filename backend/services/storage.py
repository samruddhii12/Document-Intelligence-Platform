import shutil
from pathlib import Path
from backend.config import settings

def save_file(workspace_id, document_id, filename, content: bytes):
    folder=settings.STORAGE_DIR/str(workspace_id)/str(document_id)
    folder.mkdir(parents=True,exist_ok=True)
    safe=Path(filename).name
    path=folder/safe
    path.write_bytes(content)
    return path

def delete_document_files(workspace_id, document_id):
    p=settings.STORAGE_DIR/str(workspace_id)/str(document_id)
    if p.exists(): shutil.rmtree(p)
