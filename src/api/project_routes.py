import logging
import re
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import AuthenticatedUser, get_current_user
from src.database import get_db
from src.models.db_models import Paper, Project
from src.models.project_schemas import (
    CriteriaUpdateRequest,
    KeywordSuggestionResponse,
    ProjectCreateRequest,
    ProjectResponse,
)
from src.models.schemas import PaperRecord

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


@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Module 1: List research projects for the authenticated user."""
    if user.is_admin:
        stmt = select(Project).order_by(Project.created_at.desc())
    else:
        stmt = (
            select(Project)
            .where(Project.user_id == user.id)
            .order_by(Project.created_at.desc())
        )

    result = await db.execute(stmt)
    projects = result.scalars().all()
    # Hide internal system placeholder project from user dashboard (NotebookLM style)
    visible = [p for p in projects if str(p.id) != "00000000-0000-0000-0000-000000000001" and p.name != "Default Project"]

    # Real per-project source count, server-side — the dashboard card previously
    # derived this from localStorage (device/browser-local), which showed 0 on
    # any device that hadn't locally cached that project's papers (e.g. mobile).
    if visible:
        counts_result = await db.execute(
            select(Paper.project_id, func.count(Paper.id))
            .where(Paper.project_id.in_([p.id for p in visible]))
            .group_by(Paper.project_id)
        )
        counts_by_project = dict(counts_result.all())
        for p in visible:
            p.paper_count = counts_by_project.get(p.id, 0)

    return visible


@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(
    request: ProjectCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Module 1: Create a new research project associated with the user."""
    import uuid

    # Ownership follows the verified caller. Honouring request.user_id would
    # let any caller create projects owned by someone else.
    project = Project(
        id=uuid.uuid4(),
        user_id=user.id,
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


def _resolve_project_id(pid_raw: str | UUID) -> UUID:
    if isinstance(pid_raw, UUID):
        return pid_raw
    try:
        return UUID(str(pid_raw))
    except Exception:
        return uuid.uuid5(uuid.NAMESPACE_DNS, str(pid_raw))


def _authorize_project_access(project: Project, user: AuthenticatedUser) -> None:
    """Refuse a caller who does not own this project.

    ``project.user_id`` is ``None`` for rows created before ownership was
    tracked; those are treated as accessible so existing data does not
    suddenly 404 for everyone, matching how ``list_projects`` already handles
    them for admins.
    """
    if user.is_admin:
        return
    if project.user_id is not None and project.user_id != user.id:
        raise HTTPException(status_code=403, detail="This project belongs to another account.")


@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    request: ProjectCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Module 1: Update research project details (scope, question, criteria)."""
    p_uuid = _resolve_project_id(project_id)
    result = await db.execute(select(Project).where(Project.id == p_uuid))
    project = result.scalar_one_or_none()
    if not project:
        # Create if not exists for seamless UX
        project = Project(
            id=p_uuid,
            user_id=user.id,
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

    _authorize_project_access(project, user)

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
async def get_project(
    project_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Module 1: Get project details."""
    p_uuid = _resolve_project_id(project_id)
    result = await db.execute(select(Project).where(Project.id == p_uuid))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    _authorize_project_access(project, user)
    return project

@router.get("/projects/{project_id}/papers", response_model=list[PaperRecord])
async def get_project_papers(
    project_id: str,
    decision: str = None,
    include_unverified: bool = False,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get papers for a project."""
    from sqlalchemy import func, or_

    from src.models.db_models import PageText, Paper, PDFChunk

    p_uuid = _resolve_project_id(project_id)
    parent = (await db.execute(select(Project).where(Project.id == p_uuid))).scalar_one_or_none()
    if parent:
        _authorize_project_access(parent, user)
    stmt = select(Paper).where(Paper.project_id == p_uuid)
    if not include_unverified:
        # "undetermined" is included deliberately. It means the journal was not
        # found in the local Scopus source table, which is a statement about our
        # data rather than about the paper -- most obviously on a deployment
        # where that table has not been imported at all.
        #
        # Excluding it used to make the list look empty, and the workaround for
        # that was in scopus_matcher: guess "indexed" from the publisher name
        # and invent a quartile. Showing the paper with an honest "not verified"
        # status is the version of that fix which does not put fabricated
        # rankings in the database.
        stmt = stmt.where(
            or_(
                Paper.scopus_status == "indexed",
                Paper.scopus_status == "undetermined",
                Paper.source == "direct_upload",
            )
        )
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


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Module 1: Delete a research project and all its associated child data cleanly."""
    from sqlalchemy import delete as sql_delete

    from src.models.db_models import (
        Citation,
        EvidenceExtractionAttempt,
        EvidenceRecord,
        Extraction,
        PageText,
        Paper,
        PDFChunk,
        ScreeningHistory,
        SearchQuery,
        SearchQueryPaper,
        SynthesisClaim,
        SynthesisSection,
        SynthesisSession,
        VectorCleanupJob,
    )

    p_uuid = _resolve_project_id(project_id)
    result = await db.execute(select(Project).where(Project.id == p_uuid))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    _authorize_project_access(project, user)

    # 1. Get all paper IDs
    papers_res = await db.execute(select(Paper.id).where(Paper.project_id == p_uuid))
    paper_ids = papers_res.scalars().all()

    # 2. Get all query IDs
    queries_res = await db.execute(select(SearchQuery.id).where(SearchQuery.project_id == p_uuid))
    query_ids = queries_res.scalars().all()

    # 3. Get all session IDs
    sessions_res = await db.execute(select(SynthesisSession.id).where(SynthesisSession.project_id == p_uuid))
    session_ids = sessions_res.scalars().all()

    # Delete session children
    if session_ids:
        await db.execute(sql_delete(Citation).where(Citation.synthesis_session_id.in_(session_ids)))
        await db.execute(sql_delete(SynthesisClaim).where(SynthesisClaim.synthesis_session_id.in_(session_ids)))
        await db.execute(sql_delete(SynthesisSection).where(SynthesisSection.synthesis_session_id.in_(session_ids)))
        await db.execute(sql_delete(EvidenceRecord).where(EvidenceRecord.synthesis_session_id.in_(session_ids)))
        await db.execute(sql_delete(EvidenceExtractionAttempt).where(EvidenceExtractionAttempt.synthesis_session_id.in_(session_ids)))
        await db.execute(sql_delete(SynthesisSession).where(SynthesisSession.id.in_(session_ids)))

    # Delete paper children
    if paper_ids:
        await db.execute(sql_delete(SearchQueryPaper).where(SearchQueryPaper.paper_id.in_(paper_ids)))
        # PDFChunk.page_text_id references PageText, so chunks must go first.
        await db.execute(sql_delete(PDFChunk).where(PDFChunk.paper_id.in_(paper_ids)))
        await db.execute(sql_delete(PageText).where(PageText.paper_id.in_(paper_ids)))
        await db.execute(sql_delete(Extraction).where(Extraction.paper_id.in_(paper_ids)))
        await db.execute(sql_delete(ScreeningHistory).where(ScreeningHistory.paper_id.in_(paper_ids)))
        await db.execute(sql_delete(EvidenceRecord).where(EvidenceRecord.paper_id.in_(paper_ids)))
        await db.execute(sql_delete(EvidenceExtractionAttempt).where(EvidenceExtractionAttempt.paper_id.in_(paper_ids)))
        await db.execute(sql_delete(VectorCleanupJob).where(VectorCleanupJob.paper_id.in_(paper_ids)))
        await db.execute(sql_delete(Paper).where(Paper.id.in_(paper_ids)))

    # Delete search queries
    if query_ids:
        await db.execute(sql_delete(SearchQueryPaper).where(SearchQueryPaper.search_query_id.in_(query_ids)))
        await db.execute(sql_delete(SearchQuery).where(SearchQuery.id.in_(query_ids)))

    await db.delete(project)
    await db.commit()
    return None

@router.patch("/projects/{project_id}/criteria", response_model=ProjectResponse)
async def update_criteria(
    project_id: str,
    request: CriteriaUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Module 1: Update Inclusion/Exclusion Criteria."""
    p_uuid = _resolve_project_id(project_id)
    result = await db.execute(select(Project).where(Project.id == p_uuid))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    _authorize_project_access(project, user)

    project.criteria_include = request.criteria_include
    project.criteria_exclude = request.criteria_exclude

    await db.commit()
    await db.refresh(project)
    return project

@router.post("/projects/{project_id}/suggest-keywords", response_model=KeywordSuggestionResponse)
async def suggest_keywords(
    project_id: str,
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

    # One call through the router. This handler previously carried its own
    # provider selection (an openai-or-gemini flag derived from whether
    # settings.model_name contained "gpt"), two near-identical response-parsing
    # blocks, and a catch-all that turned any failure into keywords = [] --
    # indistinguishable from "the model had no suggestions".
    from src.services.llm import NoCapableProviderError, ainvoke_with_failover

    class _Keywords(BaseModel):
        keywords: list[str] = Field(default_factory=list, max_length=7)

    try:
        result, outcome = await ainvoke_with_failover(
            "generate_keywords",
            lambda client: client.with_structured_output(_Keywords),
            [("human", prompt)],
            temperature=0.0,
        )
        keywords = [k for k in result.keywords if k.strip()][:7]
        logging.getLogger(__name__).info(
            "Keywords generated by %s (key %s).",
            outcome.selection.profile.key, outcome.selection.credential.alias,
        )
    except NoCapableProviderError:
        # Deliberately not fatal for this endpoint: suggestions are an
        # assistive feature and the researcher can type their own terms. The
        # fallback list is generic-but-honest, derived from the request rather
        # than invented by a model.
        logging.getLogger(__name__).warning(
            "No LLM provider available for keyword suggestions; using fallback terms."
        )
        keywords = []

    if not keywords:
        keywords = _fallback_keywords(request)

    return KeywordSuggestionResponse(suggested_keywords=keywords[:7])
