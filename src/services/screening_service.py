import datetime
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from src.database import get_db
from src.models.db_models import Paper, ScreeningHistory, ScreeningDecision, RelevanceBucket
from src.services.rag_service import rag_service
from src.models.screening_schemas import ScreenResponse
import uuid

logger = logging.getLogger(__name__)

async def recompute_priority(paper_id: str | uuid.UUID, db: AsyncSession):
    """Tính lại Priority Score (0-1) theo công thức ở Module 3."""
    p_id = uuid.UUID(str(paper_id)) if not isinstance(paper_id, uuid.UUID) else paper_id
    result = await db.execute(select(Paper).where(Paper.id == p_id))
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
    """Gọi Gemini LLM để phân tích chuyên sâu mức độ phù hợp của bài báo."""
    abstract = paper.abstract or ""
    if len(abstract) < 30:
        return ScreenResponse(
            relevance_bucket="insufficient_info",
            reason={"matches": [], "mismatches": ["Abstract bài báo quá ngắn hoặc chưa cập nhật để phân tích kĩ."]}
        )
        
    prompt = f"""
Bạn là chuyên gia phân tích bài báo khoa học và thẩm định tài liệu tổng quan hệ thống (Systematic Literature Review).
Hãy phân tích SÂU và CHI TIẾT bài báo sau đối với dự án nghiên cứu:

=== BỐI CẢNH NGHIÊN CỨU ===
Đề tài / Lĩnh vực: {getattr(project, 'research_field', 'Khoa học dữ liệu / AI')}
Câu hỏi nghiên cứu (Research Question): {getattr(project, 'research_question', 'Chưa xác định')}
Tiêu chí Chọn (Inclusion Criteria): {', '.join(getattr(project, 'criteria_include', []) or ['Không chỉ định'])}
Tiêu chí Loại (Exclusion Criteria): {', '.join(getattr(project, 'criteria_exclude', []) or ['Không chỉ định'])}

=== BÀI BÁO CẦN PHÂN TÍCH ===
Tên bài báo: {paper.title}
Tạp chí & Năm: {paper.journal or 'N/A'} ({paper.year or 'N/A'})
DOI: {paper.doi or 'N/A'}
Tóm tắt (Abstract): {abstract}

=== YÊU CẦU PHÂN TÍCH CHUYÊN SÂU ===
1. Đánh giá Relevance Bucket: Chọn đúng 1 trong các giá trị ["high", "medium", "low"].
2. Phân tích chi tiết thành 3 phần rõ ràng:
   - "matches": Danh sách các điểm khớp tiêu chí chọn (Inclusion) và câu hỏi nghiên cứu.
   - "mismatches": Danh sách các điểm chưa khớp, các góc cạnh nghiên cứu chưa được giải quyết hoặc điểm hạn chế của bài báo so với yêu cầu.
   - "exclusion_notes": Xác minh xem bài báo có vi phạm bất kỳ tiêu chí loại trừ (Exclusion) nào không.

=== ĐỊNH DẠNG ĐẦU RA (CHỈ TRẢ VỀ JSON KHÔNG KÈM MARKDOWN) ===
{{
    "relevance_bucket": "high",
    "reason": {{
        "matches": [
            "Khớp phương pháp & mô hình: Bài báo sử dụng mô hình 1D CNN phân loại tín hiệu ECG.",
            "Đáp ứng tiêu chí chọn (Inclusion): Viết bằng tiếng Anh và thử nghiệm trên tập dữ liệu chuẩn."
        ],
        "mismatches": [
            "Chưa đề cập đến khả năng triển khai thời gian thực trên thiết bị Edge/IoT.",
            "Phạm vi thử nghiệm mới dừng lại ở tập dữ liệu MIT-BIH, chưa mở rộng ra các dạng sóng bất thường khác."
        ],
        "exclusion_notes": [
            "Không vi phạm tiêu chí loại trừ (Exclusion)."
        ]
    }}
}}
"""
    
    # Used to build its own cascade of up to 5 hand-instantiated clients with
    # a hardcoded, gradually-deprecated model list and its own key resolution
    # order -- the same duplicated pattern that made the three Research Setup
    # agents behave by three different rules. Routing through the shared
    # ainvoke_with_failover gives screening the same model/key/failover
    # behaviour as everything else, and a model rename only has to happen once.
    from src.services.llm import ainvoke_with_failover

    try:
        result, _outcome = await ainvoke_with_failover(
            "screen_paper",
            lambda client: client.with_structured_output(ScreenResponse),
            [("human", prompt)],
            temperature=0.2,
        )
        return result
    except Exception as e:
        logger.error(f"Screening LLM call failed: {e}")
        return ScreenResponse(
            relevance_bucket="insufficient_info",
            reason={
                "matches": [],
                "mismatches": ["Hệ thống AI đang gặp tải cao hoặc gián đoạn mạng tạm thời. Vui lòng thử lại sau giây lát."],
                "exclusion_notes": []
            }
        )
