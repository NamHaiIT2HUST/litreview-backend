"""Scope Optimizer Agent — Phân tích & Tinh chỉnh phạm vi đề tài nghiên cứu.

Đo lường mức độ rộng/hẹp của câu hỏi nghiên cứu (too_broad, optimal, too_narrow)
và đề xuất 2-3 phương án câu hỏi nghiên cứu tinh gọn, chuẩn học thuật.
"""

from __future__ import annotations

import json
import logging
import os
from pydantic import BaseModel, Field

from src.config import get_settings

logger = logging.getLogger(__name__)

class ScopeAnalysisResult(BaseModel):
    status: str = Field(description="too_broad, optimal, too_narrow")
    score: int = Field(default=80, description="Độ tối ưu của phạm vi (0-100)")
    feedback: str = Field(description="Đánh giá chi tiết về phạm vi đề tài")
    suggested_topics: list[str] = Field(default_factory=list, description="2-3 câu hỏi nghiên cứu tinh chỉnh")

SCOPE_PROMPT = """Bạn là Chuyên gia Cố vấn Phương pháp luận Nghiên cứu Khoa học (Research Scope Advisor).
Hãy phân tích phạm vi của đề tài nghiên cứu sau:

- Đề tài / Câu hỏi nghiên cứu: "{idea}"
- Lĩnh vực: "{research_field}"

Nhiệm vụ của bạn:
1. Đánh giá phạm vi đề tài:
   - "too_broad": Đề tài quá rộng, chung chung, khó bao quát trong một nghiên cứu SLR cụ thể (ví dụ: "AI trong Y tế", "Ứng dụng LLM").
   - "too_narrow": Đề tài quá hẹp, quá chi tiết vào một ngữ cảnh cá biệt, khó tìm đủ bài báo quốc tế (ví dụ: "Dùng YOLOv8 nhận diện nứt xương đùi trái ở bệnh nhân 65 tuổi tại Bệnh viện X").
   - "optimal": Đề tài có phạm vi vừa vặn, đủ rõ ràng về đối tượng, phương pháp và mục tiêu.
2. Cho điểm độ tối ưu `score` từ 0 đến 100 (Điểm tối ưu là 75-95, nếu quá rộng điểm < 50, nếu quá hẹp điểm 50-65).
3. Đưa ra `feedback` (1-2 câu ngắn gọn, súc tích bằng tiếng Việt) chỉ rõ ưu điểm hoặc điểm cần thu hẹp/mở rộng.
4. Đề xuất `suggested_topics`: Đúng 2-3 câu hỏi nghiên cứu tinh chỉnh HOÀN TOÀN BẰNG TIẾNG VIỆT chuẩn học thuật, rõ ràng, sắc bén (ví dụ: "Đánh giá hiệu năng của các mô hình LLM trong...").

TRẢ VỀ DUY NHẤT MỘT JSON HỢP LỆ (KHÔNG THÊM MARKDOWN):
{{
  "status": "too_broad",
  "score": 40,
  "feedback": "Đề tài hiện tại còn khá rộng vì chưa chỉ định rõ loại robot cụ thể và bài toán ứng dụng chính (điều hướng hay thao tác).",
  "suggested_topics": [
    "Đánh giá hiệu năng của các mô hình LLM mã nguồn mở trong bài toán lập kế hoạch cho Robot di động",
    "Ứng dụng Vision-Language-Action (VLA) Models trong điều khiển cánh tay robot thao tác vật thể",
    "Khảo sát các giải pháp tối ưu độ trễ thời gian thực khi triển khai LLM trên hệ thống Robot nhúng"
  ]
}}
"""

async def run_scope_optimizer(idea: str, research_field: str = "") -> ScopeAnalysisResult:
    """Chạy Agent Cố vấn Phạm vi Đề tài với Key chuyên dụng."""
    if not idea or len(idea.strip()) < 3:
        return ScopeAnalysisResult(
            status="too_broad",
            score=20,
            feedback="Vui lòng nhập câu hỏi hoặc tên đề tài nghiên cứu cụ thể hơn.",
            suggested_topics=[]
        )

    s = get_settings()
    # Ưu tiên key chuyên dụng cho Scope Optimizer
    api_key = (
        os.getenv("GEMINI_KEY_SCOPE_OPTIMIZER")
        or s.effective_gemini_api_key
        or s.gemini_api_key
        or ""
    ).strip()

    prompt = SCOPE_PROMPT.format(idea=idea.strip(), research_field=research_field.strip() or "Khoa học máy tính / AI")

    try:
        from src.services.synthesis_llm_service import synthesis_llm_service
        llm = synthesis_llm_service._get_llm()
        msg = await llm.ainvoke([("human", prompt)])
        content = msg.content if hasattr(msg, "content") else str(msg)
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        content = str(content).strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        data = json.loads(content)
        return ScopeAnalysisResult(
            status=data.get("status", "optimal"),
            score=int(data.get("score", 80)),
            feedback=data.get("feedback", "Phạm vi nghiên cứu hợp lý."),
            suggested_topics=data.get("suggested_topics", [])
        )
    except Exception as e:
        logger.error(f"Error running scope optimizer: {e}")

    # Fallback dự phòng nếu mất mạng/hết quota
    return ScopeAnalysisResult(
        status="optimal",
        score=75,
        feedback="Đề tài có hướng đi rõ ràng. Bạn có thể thu hẹp thêm vào một bài toán cụ thể để tăng tính đột phá.",
        suggested_topics=[
            f"Ứng dụng thực nghiệm của {idea} trong bối cảnh thời gian thực",
            f"So sánh đối chuẩn hiệu năng các giải pháp cho: {idea}"
        ]
    )
