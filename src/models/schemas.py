
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000, description="Tin nhắn từ user")

class ChatResponse(BaseModel):
    response: str = Field(..., description="Phản hồi từ agent")
    analysis: str = Field(default="", description="Phân tích nội bộ")

class Paper(BaseModel):
    id: str
    title: str
    authors: str
    year: int
    abstract: str
    journal: str
    doi: str
    url: str
    citations: int
    litScore: int  # noqa: N815
    tldr: str | None = None

class SearchResponse(BaseModel):
    papers: list[Paper]
