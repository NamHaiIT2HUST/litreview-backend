from pydantic import BaseModel

class UploadResponse(BaseModel):
    file_id: str
    filename: str
    total_pages: int
    total_chunks: int
    message: str

class WorkspaceChatRequest(BaseModel):
    message: str
    # paper_id is optional if we want to filter by paper, but for now we search all chunks in the Chroma collection
    # If the user wants to chat with a specific paper, we would pass paper_id. We'll leave it out for simplicity in MVP.

class WorkspaceChatResponse(BaseModel):
    answer: str
    context_used: list[str]
