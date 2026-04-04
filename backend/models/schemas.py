from pydantic import BaseModel

class UploadResponse(BaseModel):
    session_id: str
    filename: str
