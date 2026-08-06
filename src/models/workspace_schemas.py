from pydantic import BaseModel

class UploadResponse(BaseModel):
    file_id: str
    filename: str
    total_pages: int
    total_chunks: int
    message: str
