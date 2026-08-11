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

@router.post("/papers/{paper_id}/screen", response_model=ScreenResponse)
async def screen_paper(paper_id: UUID, db: AsyncSession = Depends(get_db)):
    """Module 3: AI Screening - Gọi LLM để đánh giá relevance của bài báo."""
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
        
    project_result = await db.execute(select(Project).where(Project.id == paper.project_id))
    project = project_result.scalar_one_or_none()
    
    # Thực hiện screening
    screen_result = await screen_paper_ai(paper, project)
    
    # Cập nhật thông tin vào DB
    paper.relevance_bucket = RelevanceBucket(screen_result.relevance_bucket)
    paper.relevance_reason = screen_result.reason
    await db.commit()
    
    # Tính lại điểm
    await recompute_priority(str(paper_id), db)
    
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
