from pydantic import BaseModel, Field
from typing import List, Optional, Any

class ScreenReason(BaseModel):
    matches: List[str] = Field(default_factory=list)
    mismatches: List[str] = Field(default_factory=list)
    exclusion_notes: List[str] = Field(default_factory=list)

class ScreenResponse(BaseModel):
    relevance_bucket: str = Field(..., description="High / Medium / Low / Insufficient_info")
    # A bare `dict` field has no declared properties, so OpenAI's strict
    # structured-output mode rejects it outright ("'additionalProperties' is
    # required to be supplied and to be false") -- it only ever worked because
    # this task used to run on Gemini, whose structured output is less strict.
    reason: ScreenReason = Field(..., description="Lý do đánh giá gồm matches, mismatches, exclusion_notes")

class ScreeningDecisionRequest(BaseModel):
    decision: str = Field(..., description="keep / remove / maybe")
    note: Optional[str] = Field(None, description="Ghi chú người dùng")

class BulkScreeningDecisionRequest(BaseModel):
    paper_ids: List[str]
    decision: str = Field(..., description="keep / remove / maybe")
