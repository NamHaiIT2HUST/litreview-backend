from pydantic import BaseModel

class UploadResponse(BaseModel):
    file_id: str
    filename: str
    total_pages: int
    total_chunks: int
    message: str

class DirectUploadResponse(BaseModel):
    paper_id: str
    title: str
    filename: str
    total_pages: int
    total_chunks: int
    source: str = "direct_upload"
    message: str

class WorkspaceChatRequest(BaseModel):
    message: str
    paper_ids: list[str] = []

class WorkspaceChatResponse(BaseModel):
    answer: str
    context_used: list[str]
