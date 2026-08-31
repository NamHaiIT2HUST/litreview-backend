from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., description="Project Name")
    research_question: str = Field(..., description="The main research question")
    research_field: str = Field(..., description="Research field/domain")
    user_id: UUID | None = None
    year_from: int | None = None
    year_to: int | None = None
    criteria_include: list[str] | None = []
    criteria_exclude: list[str] | None = []

class ProjectResponse(BaseModel):
    id: UUID
    user_id: UUID | None = None
    name: str
    research_question: str
    research_field: str
    year_from: int | None = None
    year_to: int | None = None
    criteria_include: list[str] | None = []
    criteria_exclude: list[str] | None = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class CriteriaUpdateRequest(BaseModel):
    criteria_include: list[str]
    criteria_exclude: list[str]

class KeywordSuggestionResponse(BaseModel):
    suggested_keywords: list[str]
