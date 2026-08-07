from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import json

from src.database import get_db
from src.models.db_models import Project
from src.models.project_schemas import (
    ProjectCreateRequest,
    ProjectResponse,
    CriteriaUpdateRequest,
    KeywordSuggestionResponse
)

# For LLM Keyword generation
from src.services.rag_service import rag_service

router = APIRouter()

@router.post("/projects", response_model=ProjectResponse)
async def create_project(request: ProjectCreateRequest, db: AsyncSession = Depends(get_db)):
    """Module 1: Research Project Setup - Create a new project."""
    new_project = Project(
        name=request.name,
        research_question=request.research_question,
        research_field=request.research_field,
        year_from=request.year_from,
        year_to=request.year_to,
        criteria_include=request.criteria_include,
        criteria_exclude=request.criteria_exclude
    )
    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)
    return new_project

@router.patch("/projects/{project_id}/criteria", response_model=ProjectResponse)
async def update_criteria(project_id: UUID, request: CriteriaUpdateRequest, db: AsyncSession = Depends(get_db)):
    """Module 1: Update Inclusion/Exclusion Criteria."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    project.criteria_include = request.criteria_include
    project.criteria_exclude = request.criteria_exclude
    
    await db.commit()
    await db.refresh(project)
    return project

@router.post("/projects/{project_id}/suggest-keywords", response_model=KeywordSuggestionResponse)
async def suggest_keywords(project_id: UUID, db: AsyncSession = Depends(get_db)):
    """Module 1: Use AI to suggest search keywords based on the research question."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    prompt = f"""
    You are an expert academic librarian. Based on the following research project:
    Topic: {project.name}
    Field: {project.research_field}
    Question: {project.research_question}

    Suggest 5-7 highly effective search keywords or phrases for querying databases like Google Scholar or Scopus.
    Return ONLY a JSON array of strings. Do not include markdown formatting or explanations.
    Example: ["machine learning", "deep learning", "healthcare AI"]
    """
    
    try:
        response = await rag_service.llm.ainvoke(prompt)
        content = response.content
        if isinstance(content, list):
            content = content[0].get("text", "")
        content = content.strip()
        
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()
        
        keywords = json.loads(content)
        if not isinstance(keywords, list):
            keywords = []
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Keyword generation failed: {e}")
        keywords = []

    return KeywordSuggestionResponse(suggested_keywords=keywords)
