from pydantic import BaseModel, Field
from typing import List, Optional, Any

class ScreenResponse(BaseModel):
    relevance_bucket: str = Field(..., description="High / Medium / Low / Insufficient_info")
    reason: dict = Field(..., description="Lý do đánh giá gồm matches và mismatches")

class ScreeningDecisionRequest(BaseModel):
    decision: str = Field(..., description="keep / remove / maybe")
    note: Optional[str] = Field(None, description="Ghi chú người dùng")

class BulkScreeningDecisionRequest(BaseModel):
    paper_ids: List[str]
    decision: str = Field(..., description="keep / remove / maybe")
