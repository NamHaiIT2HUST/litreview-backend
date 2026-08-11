import json
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from src.database import get_db
from src.models.db_models import Paper, ScreeningHistory, ScreeningDecision, RelevanceBucket
from src.services.rag_service import rag_service
from src.models.screening_schemas import ScreenResponse

async def recompute_priority(paper_id: str, db: AsyncSession):
    """Tính lại Priority Score (0-1) theo công thức ở Module 3."""
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    if not paper:
        return
        
    relevance_weight = {
        RelevanceBucket.high: 3,
        RelevanceBucket.medium: 2,
        RelevanceBucket.low: 1,
        RelevanceBucket.insufficient_info: 0
    }
    
    scopus_weight = {
        "indexed": 2,
        "undetermined": 1,
        "not_indexed": 0
    }
    
    bucket = paper.relevance_bucket
    status = paper.scopus_status.value if paper.scopus_status else "undetermined"
    
    w_rel = relevance_weight.get(bucket, 0)
    w_scop = scopus_weight.get(status, 1)
    
    current_year = datetime.datetime.now().year
    paper_year = paper.year if paper.year else current_year
    age = current_year - paper_year
    recency = max(0, min(1, (10 - age) / 10))
    
    # Priority = (Rel * 0.5) + (Scop * 0.3) + (Rec * 0.2)
    # Trọng số tối đa: Rel (3), Scop (2), Rec (1)
    # Ta normalize Rel(0-3)/3, Scop(0-2)/2, Rec(0-1)/1
    
    norm_rel = w_rel / 3.0
    norm_scop = w_scop / 2.0
    
    score = (norm_rel * 0.5) + (norm_scop * 0.3) + (recency * 0.2)
    
    paper.priority_score = score
    await db.commit()
    return score

async def screen_paper_ai(paper: Paper, project) -> ScreenResponse:
    """Gọi LLM để phân loại relevance."""
    abstract = paper.abstract or ""
    if len(abstract) < 50:
        return ScreenResponse(
            relevance_bucket="insufficient_info",
            reason={"matches": [], "mismatches": ["Abstract quá ngắn để đánh giá."]}
        )
        
    prompt = f"""
    Bạn là một trợ lý đánh giá tài liệu học thuật. Hãy đánh giá mức độ liên quan của bài báo sau đối với dự án nghiên cứu.
    
    Research Question: {project.research_question}
    Inclusion Criteria: {', '.join(project.criteria_include) if project.criteria_include else 'Không có'}
    Exclusion Criteria: {', '.join(project.criteria_exclude) if project.criteria_exclude else 'Không có'}
    
    Paper Abstract: {abstract}
    
    Yêu cầu:
    - Đánh giá relevance bucket: "high", "medium", hoặc "low".
    - Giải thích lý do (những điểm nào khớp với criteria/question, những điểm nào không khớp).
    - Trả về ĐÚNG MỘT JSON object (KHÔNG format markdown), có định dạng:
    {{
        "relevance_bucket": "high",
        "reason": {{
            "matches": ["lý do khớp 1", "lý do khớp 2"],
            "mismatches": ["lý do không khớp 1"]
        }}
    }}
    - Không suy diễn thông tin ngoài abstract.
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
            
        data = json.loads(content)
        bucket = data.get("relevance_bucket", "low")
        if bucket not in ["high", "medium", "low", "insufficient_info"]:
            bucket = "low"
            
        return ScreenResponse(
            relevance_bucket=bucket,
            reason=data.get("reason", {"matches": [], "mismatches": []})
        )
    except Exception as e:
        print(f"Error screening paper: {e}")
        return ScreenResponse(
            relevance_bucket="insufficient_info",
            reason={"matches": [], "mismatches": ["Lỗi phân tích AI."]}
        )
