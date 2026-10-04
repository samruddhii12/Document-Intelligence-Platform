from pathlib import PurePath
from fastapi import HTTPException
from backend.config import settings

async def read_upload(file,extensions):
    filename=PurePath((file.filename or "").replace("\\","/")).name
    extension=filename.rsplit(".",1)[-1].lower() if "." in filename else ""
    if not filename or len(filename)>500 or extension not in extensions:
        raise HTTPException(400,"Supported formats: "+", ".join(sorted(extensions)))
    content=await file.read(settings.MAX_UPLOAD_MB*1024*1024+1)
    if not content: raise HTTPException(400,"The uploaded file is empty")
    if len(content)>settings.MAX_UPLOAD_MB*1024*1024: raise HTTPException(413,"File too large")
    return filename,extension,content
