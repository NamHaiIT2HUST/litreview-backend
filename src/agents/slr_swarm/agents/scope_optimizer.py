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

So sánh đề tài với 3 ví dụ mẫu dưới đây (thuộc 3 lĩnh vực khác, chỉ để bạn thấy MỨC ĐỘ cụ thể cần có ở mỗi loại, KHÔNG liên quan nội dung đề tài thực tế):

- too_broad -- "Ứng dụng công nghệ số trong giáo dục": chỉ nêu 1 công nghệ chung + 1 lĩnh vực chung, KHÔNG có bài toán cụ thể nào, KHÔNG có mục tiêu khảo sát nào (không rõ đang so sánh gì, đánh giá gì).
- optimal -- "So sánh hiệu quả học tập của mô hình lớp học đảo ngược (flipped classroom) so với giảng dạy truyền thống ở bậc đại học": có kỹ thuật/mô hình cụ thể (flipped classroom), có đối tượng cụ thể (bậc đại học, không giới hạn 1 trường/1 lớp), có mục tiêu rõ ràng (so sánh hiệu quả học tập). Đủ cụ thể để thu hẹp phạm vi tìm tài liệu, nhưng vẫn đủ tổng quát để có nhiều bài báo quốc tế.
- too_narrow -- "So sánh hiệu quả học tập giữa lớp 10A1 và 10A2 trường THPT Y trong học kỳ 1 năm 2024 khi áp dụng flipped classroom": có đủ kỹ thuật, đối tượng, mục tiêu như ví dụ optimal, NHƯNG khoá cứng vào 1 trường, 1 học kỳ, 1 năm cụ thể -- không thể tìm đủ bài báo quốc tế về đúng bối cảnh này.

Nhiệm vụ của bạn:
1. Đánh giá phạm vi đề tài theo ĐÚNG mức độ cụ thể như 3 ví dụ trên:
   - "too_broad": giống ví dụ too_broad -- chỉ nêu công nghệ/lĩnh vực chung, không có bài toán cụ thể, không có mục tiêu khảo sát rõ ràng. Một đề tài chỉ hỏi "X được dùng/ứng dụng như thế nào trong Y" (liệt kê, không có mục tiêu so sánh/đánh giá/tối ưu) luôn là too_broad, kể cả khi X, Y nghe có vẻ chuyên ngành.
   - "too_narrow": giống ví dụ too_narrow -- đã đủ cụ thể về kỹ thuật/đối tượng/mục tiêu NHƯNG khoá cứng thêm vào một ngữ cảnh cá biệt không thể tổng quát hoá (1 tổ chức/trường/bệnh viện cụ thể, 1 mốc thời gian hẹp cụ thể, 1 cá nhân/ca cụ thể, 1 địa phương cụ thể).
   - "optimal": giống ví dụ optimal -- có kỹ thuật/mô hình cụ thể, có bài toán/hệ thống/đối tượng cụ thể (không cần thêm ngữ cảnh cá biệt hoá), và có mục tiêu khảo sát rõ ràng (so sánh/tối ưu/đánh giá một khía cạnh cụ thể).
2. Cho điểm độ tối ưu `score` từ 0 đến 100 (Điểm tối ưu là 75-95, nếu quá rộng điểm < 50, nếu quá hẹp điểm 50-65).
3. Đưa ra `feedback` (1-2 câu ngắn gọn, súc tích bằng tiếng Việt) giải thích đề tài đang thiếu gì (nếu too_broad), đang bị khoá cứng vào đâu (nếu too_narrow), hoặc ưu điểm gì (nếu optimal) -- so với mức độ cụ thể của ví dụ optimal ở trên.
4. Đề xuất `suggested_topics`: Đúng 2-3 câu hỏi nghiên cứu tinh chỉnh HOÀN TOÀN BẰNG TIẾNG VIỆT chuẩn học thuật, rõ ràng, sắc bén, và PHẢI bám sát trực tiếp vào đề tài "{idea}" ở trên (thu hẹp/mở rộng đúng hướng của chính đề tài đó, không lái sang chủ đề khác).

Ví dụ định dạng JSON dưới đây thuộc một đề tài Y sinh HOÀN TOÀN KHÁC, chỉ để minh hoạ CẤU TRÚC trả về — feedback và suggested_topics của bạn phải viết mới, dựa 100% vào đề tài thực tế "{idea}", KHÔNG được sao chép nội dung ví dụ này dưới bất kỳ hình thức nào, kể cả khi đề tài thực tế trùng lĩnh vực với một lần phân tích trước đó:
{{
  "status": "too_broad",
  "score": 40,
  "feedback": "Đề tài hiện tại còn khá rộng vì chưa chỉ định rõ nhóm bệnh nhân và phương pháp chẩn đoán chính.",
  "suggested_topics": [
    "Đánh giá độ chính xác của mô hình học sâu trong tầm soát ung thư vú qua ảnh nhũ ảnh",
    "So sánh hiệu quả các thuật toán phân loại tín hiệu ECG trong phát hiện rối loạn nhịp tim",
    "Ứng dụng học chuyển giao trong chẩn đoán bệnh võng mạc tiểu đường từ ảnh đáy mắt"
  ]
}}

TRẢ VỀ DUY NHẤT MỘT JSON HỢP LỆ (KHÔNG THÊM MARKDOWN), nội dung dựa hoàn toàn vào đề tài thực tế "{idea}":
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

    try:
        # temperature=0 (not the earlier 0.3): this is a classification
        # (too_broad/optimal/too_narrow), not creative writing. At 0.3 the
        # same topic could flip verdicts between identical requests, which
        # reads as the tool being unreliable rather than the topic genuinely
        # sitting on a boundary. 0 doesn't guarantee identical output on
        # every call, but removes the deliberately-injected randomness.
        result, outcome = await ainvoke_with_failover(
            "optimize_scope",
            lambda client: client.with_structured_output(ScopeAnalysisResult),
            [("human", prompt)],
            temperature=0.0,
        )
        logger.info(
            "Scope analysed by %s (key %s) in %d attempt(s).",
            outcome.selection.profile.key, outcome.selection.credential.alias, outcome.attempts,
        )
        return result
    except Exception as exc:
        # This used to fabricate a fixed status="optimal", score=88 verdict
        # with feedback templated straight from `idea` -- indistinguishable
        # from a real judgment, so a transient provider failure silently told
        # the researcher their scope was fine without ever being evaluated.
        # The frontend already renders a distinct "error" badge (⚠️ Tạm thời
        # gián đoạn); it just never received this status. Report the failure
        # honestly instead of guessing a verdict.
        logger.warning("LLM call failed in run_scope_optimizer: %s", exc)
        return ScopeAnalysisResult(
            status="error",
            score=0,
            feedback="Hệ thống AI tạm thời không đánh giá được phạm vi đề tài (lỗi kết nối hoặc quá tải model). Vui lòng thử lại sau ít phút.",
            suggested_topics=[]
        )
