from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID

class ProjectCreateRequest(BaseModel):
    name: str = Field(..., description="Project Name")
    research_question: str = Field(..., description="The main research question")
    research_field: str = Field(..., description="Research field/domain")
    user_id: Optional[UUID] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    criteria_include: Optional[List[str]] = []
    criteria_exclude: Optional[List[str]] = []

class ProjectResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    name: str
    research_question: str
    research_field: str
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    criteria_include: Optional[List[str]] = []
    criteria_exclude: Optional[List[str]] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class CriteriaUpdateRequest(BaseModel):
    criteria_include: List[str]
    criteria_exclude: List[str]

class KeywordSuggestionResponse(BaseModel):
    suggested_keywords: List[str]
