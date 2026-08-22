from pydantic import BaseModel, Field
from typing import List, Optional

class SearchStrategy(BaseModel):
    label: str
    query_string: str
    result_count: int

class SearchStrategiesResponse(BaseModel):
    strategies: List[SearchStrategy]

class SearchExecuteRequest(BaseModel):
    query_string: str = Field(..., description="Từ khóa tìm kiếm (boolean query)")
    strategy_label: Optional[str] = Field(None, description="Tên chiến lược nếu chọn từ AI gợi ý")

class PaperToRerank(BaseModel):
    id: str
    title: str
    abstract: str
    original_score: Optional[float] = 0.0

class RerankRequest(BaseModel):
    query: str
    papers: List[PaperToRerank]

class RerankedPaper(PaperToRerank):
    relevance_score: float

class RerankResponse(BaseModel):
    results: List[RerankedPaper]

