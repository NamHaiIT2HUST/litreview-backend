from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import json
import re
import os

from src.database import get_db
from src.models.db_models import Project
from src.models.project_schemas import (
    ProjectCreateRequest,
    ProjectResponse,
    CriteriaUpdateRequest,
    KeywordSuggestionResponse
)
from src.models.schemas import PaperRecord
from src.services.rag_service import rag_service

router = APIRouter()


def _fallback_keywords(request: ProjectCreateRequest) -> list[str]:
    """Return a keyword set grounded in the research question and inclusion criteria.
    
    Generic implementation — works for any research topic by extracting
    meaningful phrases from the user's input rather than hardcoding
    domain-specific terms.
    """
    phrases: list[str] = []

    def add_phrase(value: str | None) -> None:
        if not value:
            return
        text = re.sub(r"\s+", " ", str(value)).strip(" ,.-")
        if text:
            phrases.append(text)

    # Build from research intent + inclusion criteria
    add_phrase(request.research_field)
    add_phrase(request.research_question)
    for item in request.criteria_include or []:
        add_phrase(item)

    # Deduplicate while preserving order
    result: list[str] = []
    seen: set[str] = set()
    for phrase in phrases:
        key = phrase.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(phrase)
        if len(result) >= 7:
            break

    if not result:
        result = ["systematic review", "machine learning", "deep learning"]

    return result[:7]


def _extract_user_info(authorization: Optional[str], x_user_id: Optional[str]) -> tuple[Optional[UUID], Optional[str]]:
    """Extracts (user_id, role) from JWT token or X-User-Id header."""
    import jwt
    from src.api.auth_routes import SECRET_KEY, ALGORITHM
    
    if authorization and authorization.startswith("Bearer "):
        token = authorization[len("Bearer "):].strip()
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id_str = payload.get("id")
            role = payload.get("role")
            if user_id_str:
                return UUID(str(user_id_str)), role
        except Exception:
            pass

    if x_user_id:
        try:
            return UUID(str(x_user_id)), "user"
        except Exception:
            pass

    return None, None


@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Module 1: List research projects for the authenticated user."""
    user_id, role = _extract_user_info(authorization, x_user_id)

    if role == "admin":
        stmt = select(Project).order_by(Project.created_at.desc())
    elif user_id:
        stmt = select(Project).where(Project.user_id == user_id).order_by(Project.created_at.desc())
    else:
        stmt = select(Project).where(Project.user_id.is_(None)).order_by(Project.created_at.desc())

    result = await db.execute(stmt)
    projects = result.scalars().all()
    return projects


@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(
    request: ProjectCreateRequest,
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Module 1: Create a new research project associated with the user."""
    import uuid
    user_id, _ = _extract_user_info(authorization, x_user_id)
    final_user_id = request.user_id or user_id

    project = Project(
        id=uuid.uuid4(),
        user_id=final_user_id,
        name=request.name,
        research_question=request.research_question,
        research_field=request.research_field,
        year_from=request.year_from,
        year_to=request.year_to,
        criteria_include=request.criteria_include,
        criteria_exclude=request.criteria_exclude,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    request: ProjectCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Module 1: Update research project details (scope, question, criteria)."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.name = request.name
    project.research_question = request.research_question
    project.research_field = request.research_field
    project.year_from = request.year_from
    project.year_to = request.year_to
    project.criteria_include = request.criteria_include
    project.criteria_exclude = request.criteria_exclude

    await db.commit()
    await db.refresh(project)
    return project


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: UUID, db: AsyncSession = Depends(get_db)):
    """Module 1: Get project details."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.get("/projects/{project_id}/papers", response_model=list[PaperRecord])
async def get_project_papers(
    project_id: UUID,
    decision: str = None,
    include_unverified: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Get papers for a project.

    By default this returns only Scopus-verified papers so the Search view and
    history stay aligned with the Google Scholar -> Scopus acceptance flow.
    """
    from sqlalchemy import or_, func
    from src.models.db_models import Paper, PageText, PDFChunk
    
    stmt = select(Paper).where(Paper.project_id == project_id)
    if not include_unverified:
        stmt = stmt.where(or_(Paper.scopus_status == "indexed", Paper.source == "direct_upload"))
    if decision:
        stmt = stmt.where(Paper.screening_decision == decision)
        
    result = await db.execute(stmt)
    papers = result.scalars().all()
    
    paper_records = []
    for p in papers:
        record = PaperRecord.model_validate(p)
        if p.source == "direct_upload":
            pages_stmt = select(func.count(PageText.id)).where(PageText.paper_id == p.id)
            chunks_stmt = select(func.count(PDFChunk.id)).where(PDFChunk.paper_id == p.id)
            
            pages_res = await db.execute(pages_stmt)
            chunks_res = await db.execute(chunks_stmt)
            
            record.total_pages = pages_res.scalar_one()
            record.total_chunks = chunks_res.scalar_one()
        paper_records.append(record)
        
    return paper_records

@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: UUID, request: ProjectCreateRequest, db: AsyncSession = Depends(get_db)):
    """Module 1: Update an existing project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    project.name = request.name
    project.research_question = request.research_question
    project.research_field = request.research_field
    project.year_from = request.year_from
    project.year_to = request.year_to
    project.criteria_include = request.criteria_include
    project.criteria_exclude = request.criteria_exclude
    
    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(project_id: UUID, db: AsyncSession = Depends(get_db)):
    """Module 1: Delete a research project and its associated papers."""
    from src.models.db_models import Paper, PageText, PDFChunk
    from sqlalchemy import delete as sql_delete

    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Delete related papers and text chunks
    papers_res = await db.execute(select(Paper.id).where(Paper.project_id == project_id))
    paper_ids = papers_res.scalars().all()
    if paper_ids:
        await db.execute(sql_delete(PageText).where(PageText.paper_id.in_(paper_ids)))
        await db.execute(sql_delete(PDFChunk).where(PDFChunk.paper_id.in_(paper_ids)))
        await db.execute(sql_delete(Paper).where(Paper.id.in_(paper_ids)))

    await db.delete(project)
    await db.commit()
    return None

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
async def suggest_keywords(
    project_id: UUID,
    request: ProjectCreateRequest,
    x_gemini_key: str | None = Header(None, description="Gemini API Key (user-provided)"),
    db: AsyncSession = Depends(get_db),
):
    """Module 1: Use Gemini AI to suggest search keywords based on research config + screening criteria."""

    prompt = f"""You are an expert academic librarian and systematic review search strategist.
Your task: generate the BEST English-language search keywords for finding relevant Scopus-indexed papers on Google Scholar.

=== RESEARCH CONTEXT ===
Project name: {request.name}
Research question: {request.research_question}
Field/Domain: {request.research_field}
Year range: {request.year_from or 'any'} – {request.year_to or 'any'}

=== SCREENING CRITERIA ===
Inclusion (papers MUST have): {', '.join(request.criteria_include or ['not specified'])}
Exclusion (papers MUST NOT have): {', '.join(request.criteria_exclude or ['not specified'])}

=== INSTRUCTIONS ===
1. Analyze the research question deeply. Identify the core CONCEPTS, METHODS, and DOMAIN.
2. ALL keywords must be in ENGLISH — academic English used in paper titles and abstracts.
3. Generate keywords that researchers would actually use as paper titles, abstract terms, or index keywords.
4. Include both specific technical terms AND broader field terms.
5. Create at least 2 Boolean-style search strings (using AND/OR/quotes) that can be pasted directly into Google Scholar.
6. The inclusion criteria tell you WHAT to include — extract searchable terms from them.
7. The exclusion criteria tell you what to AVOID — do NOT generate keywords matching exclusions.
8. Prioritize terms that will find papers IN Scopus-indexed journals.

=== OUTPUT FORMAT ===
Return ONLY a JSON array of exactly 7 strings. All in English. Mix individual keywords with Boolean search strings.
Example: ["ECG classification 1D CNN", "one-dimensional convolutional neural network electrocardiogram", "1D CNN arrhythmia detection", "deep learning ECG signal", "time-series classification neural network", "ECG AND \\"1D CNN\\" AND classification", "cardiac signal deep learning model"]
"""

    # Determine Gemini API key: header > .env GEMINI_API_KEY > .env GOOGLE_API_KEY
    from src.config import get_settings
    settings = get_settings()
    gemini_key = x_gemini_key if isinstance(x_gemini_key, str) else ""
    gemini_key = gemini_key.strip()
    if not gemini_key:
        gemini_key = settings.effective_gemini_api_key

    keywords: list[str] = []

    # Decide provider
    use_openai = False
    if settings.openai_api_key and (
        "gpt" in settings.model_name.lower() or not gemini_key
    ):
        use_openai = True

    if use_openai:
        try:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                model=settings.model_name,
                openai_api_key=settings.openai_api_key,
                openai_api_base=settings.get_api_base or None,
                temperature=0.0
            )
            # Use sync invoke since it's cleaner in this handler
            response = llm.invoke(prompt)
            content = response.content.strip()

            # Clean markdown fences and extract JSON
            try:
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    content = json_match.group(0)
                parsed = json.loads(content)
                if isinstance(parsed, list):
                    keywords = [str(x) for x in parsed][:7]
                else:
                    keywords = []
            except json.JSONDecodeError as je:
                import logging
                logging.getLogger(__name__).warning(f"Failed to parse JSON from OpenAI: {content} - Error: {je}")
                keywords = []
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"OpenAI keyword generation failed: {e}")

    elif gemini_key:
        try:
            from google import genai

            client = genai.Client(api_key=gemini_key)
            gemini_model = settings.model_name
            if "gemini" not in gemini_model.lower():
                gemini_model = "gemini-1.5-flash"

            response = client.models.generate_content(
                model=gemini_model,
                contents=prompt,
            )
            content = response.text.strip()

            # Clean markdown fences and extract JSON
            try:
                # Attempt to find JSON array anywhere in the text
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    content = json_match.group(0)
                parsed = json.loads(content)
                if isinstance(parsed, list):
                    keywords = [str(x) for x in parsed][:7]
                else:
                    keywords = []
            except json.JSONDecodeError as je:
                import logging
                logging.getLogger(__name__).warning(f"Failed to parse JSON: {content} - Error: {je}")
                keywords = []
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Gemini keyword generation failed: {e}")
    else:
        import logging
        logging.getLogger(__name__).warning(
            "No API key available for OpenAI/Gemini. Using fallback keywords."
        )

    if not keywords:
        keywords = _fallback_keywords(request)

    return KeywordSuggestionResponse(suggested_keywords=keywords[:7])
