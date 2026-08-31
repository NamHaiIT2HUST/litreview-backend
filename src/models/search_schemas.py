
from pydantic import BaseModel, Field


class SearchStrategy(BaseModel):
    label: str
    query_string: str
    result_count: int

class SearchStrategiesResponse(BaseModel):
    strategies: list[SearchStrategy]

class SearchExecuteRequest(BaseModel):
    query_string: str = Field(..., description="Từ khóa tìm kiếm (boolean query)")
    strategy_label: str | None = Field(None, description="Tên chiến lược nếu chọn từ AI gợi ý")

class PaperToRerank(BaseModel):
    id: str
    title: str
    abstract: str
    original_score: float | None = 0.0

class RerankRequest(BaseModel):
    query: str
    papers: list[PaperToRerank]

class RerankedPaper(PaperToRerank):
    relevance_score: float

class RerankResponse(BaseModel):
    results: list[RerankedPaper]

