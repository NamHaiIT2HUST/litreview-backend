"""Criteria Generator Agent — Tự động sinh tiêu chí Inclusion/Exclusion chuẩn học thuật.

Đọc câu hỏi nghiên cứu và lĩnh vực, tự động đề xuất 3 tiêu chí chọn (Inclusion)
và 3 tiêu chí loại (Exclusion) chuẩn quốc tế.
"""

from __future__ import annotations

import json
import logging
import os
from pydantic import BaseModel, Field

from src.config import get_settings

logger = logging.getLogger(__name__)

class CriteriaGenerationResult(BaseModel):
    criteria_include: list[str] = Field(default_factory=list, description="Danh sách tiêu chí chọn vào (Inclusion)")
    criteria_exclude: list[str] = Field(default_factory=list, description="Danh sách tiêu chí loại trừ (Exclusion)")

CRITERIA_PROMPT = """Bạn là Chuyên gia Tổng quan Hệ thống (Systematic Literature Review Expert).
Dựa trên đề tài nghiên cứu sau:

- Đề tài / Câu hỏi nghiên cứu: "{idea}"
- Lĩnh vực: "{research_field}"

Hãy tự động đề xuất:
1. "criteria_include" (Đúng 3-4 tiêu chí chọn vào quan trọng nhất):
   - Thời gian xuất bản (ví dụ: Các công trình từ 2021 đến nay)
   - Phương pháp & Nội dung (ví dụ: Có thử nghiệm thực nghiệm / triển khai trên mô hình thực tế hoặc môi trường giả lập chuẩn)
   - Dạng bài & Ngôn ngữ (ví dụ: Bài báo có bình duyệt - Peer-reviewed, viết bằng tiếng Anh)
2. "criteria_exclude" (Đúng 3-4 tiêu chí loại trừ chặt chẽ nhất):
   - Dạng tài liệu kém tin cậy (ví dụ: Sách tóm tắt, bài quan điểm cá nhân, bài báo chưa qua bình duyệt)
   - Phạm vi nghiên cứu không liên quan (ví dụ: Nghiên cứu lý thuyết thuần túy không có dữ liệu đối sánh hiệu năng)
   - Dữ liệu bị trùng lặp hoặc thiếu thông tin thực nghiệm

TRẢ VỀ DUY NHẤT MỘT JSON HỢP LỆ (KHÔNG THÊM MARKDOWN):
{{
  "criteria_include": [
    "Bài báo được xuất bản từ năm 2021 đến nay (đảm bảo tính cập nhật của công nghệ)",
    "Nghiên cứu có thử nghiệm thực nghiệm trên Robot thật hoặc môi trường mô phỏng chuẩn (Gazebo, Isaac Sim, MuJoCo)",
    "Bài báo được bình duyệt (Peer-reviewed) xuất bản tại các tạp chí, hội nghị uy tín bằng tiếng Anh"
  ],
  "criteria_exclude": [
    "Các bài báo ngắn (Short papers < 3 trang), bài tóm tắt hội thảo, bài viết ý kiến (Editorial/Opinion)",
    "Các nghiên cứu lý thuyết trừu tượng không cung cấp mã nguồn, tập dữ liệu hoặc kết quả đo lường cụ thể",
    "Các tài liệu không được viết bằng tiếng Anh hoặc bản sao trùng lặp nội dung"
  ]
}}
"""

async def run_criteria_generator(idea: str, research_field: str = "") -> CriteriaGenerationResult:
    """Chạy Agent Tự động Sinh Tiêu chí với Key chuyên dụng."""
    if not idea or len(idea.strip()) < 3:
        return CriteriaGenerationResult(
            criteria_include=["Bài báo xuất bản từ 2021 đến nay", "Có thử nghiệm thực nghiệm", "Viết bằng tiếng Anh"],
            criteria_exclude=["Bài tóm tắt hội thảo ngắn", "Không có số liệu đối chứng", "Tài liệu trùng lặp"]
        )

    s = get_settings()
    from src.services.lora_client import call_lora_model
    
    # 1. THỬ GỌI LORA MODEL TRƯỚC (NẾU CÓ)
    lora_instruction = "Generate rigorous PRISMA inclusion and exclusion criteria."
    lora_input = f"Domain: {research_field}\nTopic: {idea}"
    lora_result = await call_lora_model("lora_agent2_criteria", lora_instruction, lora_input)
    if lora_result:
        return CriteriaGenerationResult(
            criteria_include=lora_result.get("include", lora_result.get("criteria_include", [])),
            criteria_exclude=lora_result.get("exclude", lora_result.get("criteria_exclude", []))
        )
        
    # 2. NẾU LORA OFF, FALLBACK SANG GEMINI
    # Ưu tiên key chuyên dụng cho Criteria Generator
    api_key = (
        os.getenv("GEMINI_KEY_CRITERIA_GENERATOR")
        or s.effective_gemini_api_key
        or s.gemini_api_key
        or ""
    ).strip()

    prompt = CRITERIA_PROMPT.format(idea=idea.strip(), research_field=research_field.strip() or "Khoa học máy tính / AI")

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        config = types.GenerateContentConfig(
            temperature=0.2,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )

        models_to_try = ["gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-flash-latest"]
        for m in models_to_try:
            try:
                res = await client.aio.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=config,
                )
                if res and res.text:
                    content = res.text.strip()
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0].strip()
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0].strip()
                    
                    data = json.loads(content)
                    return CriteriaGenerationResult(
                        criteria_include=data.get("criteria_include", []),
                        criteria_exclude=data.get("criteria_exclude", [])
                    )
            except Exception as ex:
                logger.warning(f"Criteria generator with model {m} failed: {ex}")
                continue
    except Exception as e:
        logger.error(f"Error running criteria generator: {e}")

    # Fallback
    return CriteriaGenerationResult(
        criteria_include=[
            "Bài báo xuất bản từ năm 2021 đến nay (bảo đảm tính mới)",
            "Nghiên cứu có triển khai thử nghiệm thực tế hoặc trên tập dữ liệu chuẩn",
            "Công trình có bình duyệt (Peer-reviewed) xuất bản bằng tiếng Anh"
        ],
        criteria_exclude=[
            "Tài liệu hội thảo dạng tóm tắt ngắn (Extended Abstract < 3 trang)",
            "Nghiên cứu lý thuyết thuần túy không có số liệu đối chuẩn định lượng",
            "Tài liệu không viết bằng tiếng Anh hoặc trùng lặp dữ liệu"
        ]
    )
