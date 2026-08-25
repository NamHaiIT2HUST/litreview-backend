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
        
    # 2. GỌI LLM VỚI ĐA NHÀ CUNG CẤP (Gemini, Groq, OpenAI)
    prompt = CRITERIA_PROMPT.format(idea=idea.strip(), research_field=research_field.strip() or "Khoa học máy tính / AI")

    keys = s.all_gemini_api_keys
    gemini_key = (os.getenv("GEMINI_KEY_CRITERIA_GENERATOR") or (keys[1] if len(keys) > 1 else (keys[0] if len(keys) > 0 else "")) or s.gemini_api_key or os.getenv("GOOGLE_API_KEY") or "").strip()
    groq_key = (os.getenv("GROQ_API_KEY") or s.groq_api_key or "").strip()
    openai_key = (os.getenv("OPENAI_API_KEY") or s.effective_openai_api_key or s.openai_api_key or "").strip()

    llm_candidates = []
    if gemini_key:
        from langchain_google_genai import ChatGoogleGenerativeAI
        for m in ["gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-flash-latest"]:
            try:
                llm_candidates.append(ChatGoogleGenerativeAI(model=m, google_api_key=gemini_key, temperature=0.3, max_retries=1))
            except Exception:
                pass

    if groq_key:
        try:
            from langchain_groq import ChatGroq
            llm_candidates.append(ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=groq_key, temperature=0.3, max_retries=1))
        except Exception:
            pass

    if openai_key:
        try:
            from langchain_openai import ChatOpenAI
            llm_candidates.append(ChatOpenAI(
                model=s.effective_model_name or "deepseek/deepseek-v3.2",
                openai_api_key=openai_key,
                base_url=s.get_api_base or None,
                temperature=0.3,
                max_retries=1,
                timeout=10,
            ))
        except Exception:
            pass

    try:
        from src.services.synthesis_llm_service import synthesis_llm_service
        fallback_llm = synthesis_llm_service._get_llm()
        if fallback_llm:
            llm_candidates.append(fallback_llm)
    except Exception:
        pass

    import asyncio
    for candidate in llm_candidates:
        try:
            msg = await asyncio.wait_for(candidate.ainvoke([("human", prompt)]), timeout=10.0)
            content = msg.content if hasattr(msg, "content") else str(msg)
            if isinstance(content, list):
                content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
            content = str(content).strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            data = json.loads(content)
            return CriteriaGenerationResult(
                criteria_include=data.get("criteria_include", []),
                criteria_exclude=data.get("criteria_exclude", [])
            )
        except Exception as e:
            last_error = e
            logger.error(f"Error running criteria generator with LLM: {e}")

    # Xử lý thông báo lỗi chi tiết khi hết Quota hoặc Timeout
    error_str = str(last_error).lower() if 'last_error' in locals() and last_error else ""
    if "429" in error_str or "resource_exhausted" in error_str or "quota" in error_str or "rate limit" in error_str:
        return CriteriaGenerationResult(
            criteria_include=["⚠️ Hệ thống đang tạm thời hết hạn mức AI (Quota Exceeded). Vui lòng thử lại sau 1-2 phút."],
            criteria_exclude=["⚠️ Vui lòng cấu hình thêm API Key hoặc thử lại sau ít phút."]
        )
    elif "timeout" in error_str or "timed out" in error_str or "deadline" in error_str or "connection" in error_str:
        return CriteriaGenerationResult(
            criteria_include=["⏳ Hệ thống đang gặp sự cố phản hồi chậm (Request Timeout). Vui lòng thử lại vào lúc khác."],
            criteria_exclude=["⏳ Kết nối mạng gián đoạn khi sinh tiêu chí."]
        )
    elif 'last_error' in locals() and last_error:
        return CriteriaGenerationResult(
            criteria_include=[f"⚠️ Lỗi kết nối AI ({type(last_error).__name__}). Vui lòng thử lại."],
            criteria_exclude=["⚠️ Vui lòng nhấn 'Gợi ý tiêu chí bằng AI' để thử lại."]
        )

    # Fallback mặc định
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
