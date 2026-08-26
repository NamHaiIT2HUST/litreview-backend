"""Scope Optimizer Agent — Phân tích & Tinh chỉnh phạm vi đề tài nghiên cứu.

Đo lường mức độ rộng/hẹp của câu hỏi nghiên cứu (too_broad, optimal, too_narrow)
và đề xuất 2-3 phương án câu hỏi nghiên cứu tinh gọn, chuẩn học thuật.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from src.services.llm import ainvoke_with_failover

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

    from src.services.lora_client import call_lora_model

    # 1. THỬ GỌI LORA MODEL TRƯỚC (NẾU CÓ)
    lora_instruction = "Evaluate the research scope and suggest refinements."
    lora_input = f"Domain: {research_field}\nTopic: {idea}"
    lora_result = await call_lora_model("lora_agent1_scope", lora_instruction, lora_input)
    if lora_result:
        return ScopeAnalysisResult(
            status=lora_result.get("status", "optimal"),
            score=lora_result.get("score", 85),
            feedback=lora_result.get("feedback", "Đã phân tích phạm vi bằng mô hình LoRA chuyên dụng."),
            suggested_topics=lora_result.get("suggested_topics", [])
        )

    # 2. Gọi LLM qua router chung.
    #
    # Khối cũ tự dựng tới 5 client, đọc key Gemini theo vị trí (`keys[0]`), và
    # khi mọi provider hỏng thì trả thông báo lỗi trong trường `feedback` —
    # nghĩa là chuỗi "Hệ thống đang gặp lỗi quá tải hạn mức AI" đi vào đúng ô
    # dành cho nhận xét học thuật về phạm vi nghiên cứu, với HTTP 200.
    prompt = SCOPE_PROMPT.format(idea=idea.strip(), research_field=research_field.strip() or "Khoa học máy tính / AI")

    result, outcome = await ainvoke_with_failover(
        "optimize_scope",
        lambda client: client.with_structured_output(ScopeAnalysisResult),
        [("human", prompt)],
        temperature=0.3,
    )
    logger.info(
        "Scope analysed by %s (key %s) in %d attempt(s).",
        outcome.selection.profile.key, outcome.selection.credential.alias, outcome.attempts,
    )
    return result
