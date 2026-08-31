
from pydantic import BaseModel, Field


class ScreenReason(BaseModel):
    matches: list[str] = Field(default_factory=list)
    mismatches: list[str] = Field(default_factory=list)
    exclusion_notes: list[str] = Field(default_factory=list)

class ScreenResponse(BaseModel):
    relevance_bucket: str = Field(..., description="High / Medium / Low / Insufficient_info")
    # A bare `dict` field has no declared properties, so OpenAI's strict
    # structured-output mode rejects it outright ("'additionalProperties' is
    # required to be supplied and to be false") -- it only ever worked because
    # this task used to run on Gemini, whose structured output is less strict.
    reason: ScreenReason = Field(..., description="Lý do đánh giá gồm matches, mismatches, exclusion_notes")

class ScreeningDecisionRequest(BaseModel):
    decision: str = Field(..., description="keep / remove / maybe")
    note: str | None = Field(None, description="Ghi chú người dùng")

class BulkScreeningDecisionRequest(BaseModel):
    paper_ids: list[str]
    decision: str = Field(..., description="keep / remove / maybe")
