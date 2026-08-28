from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import uuid

from src.database import get_db
from src.models.db_models import Paper, ScreeningHistory, ScreeningDecision, Project, RelevanceBucket
from src.models.screening_schemas import ScreenResponse, ScreeningDecisionRequest, BulkScreeningDecisionRequest
from src.services.screening_service import screen_paper_ai, recompute_priority

router = APIRouter()

from pydantic import BaseModel
from typing import Optional, Any
from src.config import get_settings

class PaperScreenPayload(BaseModel):
    title: Optional[str] = None
    abstract: Optional[str] = None
    journal: Optional[str] = None
    year: Optional[int] = None
    doi: Optional[str] = None
    authors: Optional[Any] = None
    # A fresh search result isn't written to `papers` until the researcher
    # explicitly keeps it, so `paper_id` here is routinely a client-side-only
    # ID that matches no DB row. Without this, the project lookup below fell
    # back to a hardcoded default project -- meaning "AI Screening" silently
    # judged the paper against whatever criteria that unrelated default
    # project happened to hold, not the project actually open on screen.
    project_id: Optional[str] = None

@router.post("/papers/{paper_id}/screen", response_model=ScreenResponse)
async def screen_paper(paper_id: str, payload: Optional[PaperScreenPayload] = None, db: AsyncSession = Depends(get_db)):
    """Module 3: AI Screening - Gọi LLM để đánh giá relevance của bài báo."""
    paper = None
    try:
        p_uuid = uuid.UUID(str(paper_id))
        result = await db.execute(select(Paper).where(Paper.id == p_uuid))
        paper = result.scalar_one_or_none()
    except Exception:
        pass

    DEFAULT_PROJECT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
    request_project_id = None
    if payload and payload.project_id:
        try:
            request_project_id = uuid.UUID(str(payload.project_id))
        except Exception:
            request_project_id = None

    # The title-based fallback lookups below used to search the ENTIRE
    # `papers` table with no project filter -- a title that happens to
    # fuzzy-match a paper in a completely unrelated project would win, and
    # everything downstream (which criteria to screen against, and which
    # row's relevance_bucket gets overwritten at the end of this function)
    # would silently apply to that unrelated project instead of the one
    # actually open on screen. Scope the lookup to the requesting project
    # whenever we know it, so a same-titled paper elsewhere is never mistaken
    # for this one.
    title_query_filters = []
    if request_project_id:
        title_query_filters.append(Paper.project_id == request_project_id)

    if not paper and payload and payload.title:
        query = select(Paper).where(Paper.title.ilike(f"%{payload.title.strip()}%"), *title_query_filters)
        result = await db.execute(query)
        paper = result.scalars().first()

    if not paper and paper_id and len(paper_id) > 3:
        query = select(Paper).where(Paper.title.ilike(f"%{paper_id}%"), *title_query_filters)
        result = await db.execute(query)
        paper = result.scalars().first()

    # Which project's criteria to screen against: always prefer the project
    # explicitly open on screen (what the frontend just sent) over whatever
    # project the matched DB row happens to belong to -- the researcher is
    # judging this paper against the SLR they're currently working in, not
    # whichever project a stray title match landed in.
    if request_project_id:
        effective_project_id = request_project_id
    elif paper:
        effective_project_id = paper.project_id
    else:
        effective_project_id = DEFAULT_PROJECT_ID

    project_result = await db.execute(select(Project).where(Project.id == effective_project_id))
    project = project_result.scalar_one_or_none()

    if not paper:
        if payload and payload.title:
            authors_str = str(payload.authors) if payload.authors else "Unknown Authors"
            paper = Paper(
                id=uuid.uuid4(),
                project_id=effective_project_id,
                title=payload.title,
                abstract=payload.abstract or "",
                journal=payload.journal or "Academic Journal",
                year=payload.year or 2024,
                doi=payload.doi or "N/A",
                authors=authors_str
            )
        else:
            raise HTTPException(status_code=404, detail="Paper not found")
        
    # Thực hiện screening
    screen_result = await screen_paper_ai(paper, project)
    
    # Cập nhật thông tin vào DB nếu paper đã tồn tại trong DB
    try:
        paper.relevance_bucket = RelevanceBucket(screen_result.relevance_bucket)
        paper.relevance_reason = screen_result.reason.model_dump()
        await db.commit()
        await recompute_priority(str(paper.id), db)
    except Exception:
        pass
    
    return screen_result


@router.post("/papers/{paper_id}/screening-decision")
async def make_decision(paper_id: UUID, request: ScreeningDecisionRequest, db: AsyncSession = Depends(get_db)):
    """Module 3: Lưu quyết định Screening của người dùng cho 1 bài báo."""
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
        
    decision_enum = ScreeningDecision(request.decision)
    
    history_record = ScreeningHistory(
        id=uuid.uuid4(),
        paper_id=paper_id,
        decision=decision_enum,
        ai_reason=paper.relevance_reason,
        user_note=request.note
    )
    db.add(history_record)
    
    paper.screening_decision = decision_enum
    await db.commit()
    
    return {"status": "success", "decision": request.decision}


@router.post("/papers/bulk-decision")
async def bulk_decision(request: BulkScreeningDecisionRequest, db: AsyncSession = Depends(get_db)):
    """Module 3: Bulk Update quyết định cho nhiều bài báo (giới hạn 50)."""
    if len(request.paper_ids) > 50:
        raise HTTPException(status_code=400, detail="Too many papers in one request (max 50).")
        
    decision_enum = ScreeningDecision(request.decision)
    
    # Fetch papers
    stmt = select(Paper).where(Paper.id.in_(request.paper_ids))
    result = await db.execute(stmt)
    papers = result.scalars().all()
    
    for paper in papers:
        paper.screening_decision = decision_enum
        history = ScreeningHistory(
            id=uuid.uuid4(),
            paper_id=paper.id,
            decision=decision_enum,
            ai_reason=paper.relevance_reason,
        )
        db.add(history)
        
    await db.commit()
    return {"status": "success", "updated_count": len(papers)}
