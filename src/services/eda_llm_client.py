"""LLM client for the "Phân tích dữ liệu" (EDA / Data Analysis) workspace tab only.

Deliberately self-contained -- does not import from synthesis_llm_service.py
(the "Tổng hợp tài liệu" / multi-paper synthesis pipeline) and does not touch
OPENAI_API_KEY (which belongs to the centralized router in src/services/llm/,
used by the Cấu hình and Tìm kiếm tabs). Editing this file can only affect the
Phân tích tab; editing synthesis_llm_service.py or src/services/llm/ can only
affect their own tabs. Uses its own env vars: LLM_API_KEY, LLM_MODEL,
LLM_API_BASE, LLM_TEMPERATURE.
"""
from __future__ import annotations

from langchain_openai import ChatOpenAI


def build_eda_llm(settings, *, openai_cls=None):
    """Construct the chat client used by workspace_analyze_data() in routes.py."""
    api_key = settings.llm_api_key
    if not api_key:
        raise RuntimeError(
            "No API key configured for the 'Phân tích dữ liệu' tab. Set LLM_API_KEY "
            "(and LLM_API_BASE / LLM_MODEL) in .env -- this is separate from "
            "OPENAI_API_KEY, which belongs to the Cấu hình/Tìm kiếm tabs' router."
        )
    model = settings.llm_model or "deepseek/deepseek-v3.2"

    kwargs = {
        "model": model,
        "api_key": api_key,
        "temperature": settings.llm_temperature,
        "max_tokens": 8192,
        "max_retries": 1,
        "timeout": 15,
        "default_headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    }
    if settings.llm_api_base:
        kwargs["base_url"] = settings.llm_api_base

    cls = openai_cls or ChatOpenAI
    return cls(**kwargs)
