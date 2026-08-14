import asyncio
from types import SimpleNamespace

import pytest

from src.services.synthesis_llm_service import (
    SynthesisLLMService,
    _is_transient_provider_error,
    create_synthesis_llm,
)


class FakeChatModel:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


def settings(**overrides):
    values = {
        "synthesis_llm_provider": "gemini",
        "synthesis_model": "gemini-3.5-flash-lite",
        "synthesis_temperature": 0.0,
        "gemini_api_key": "gemini-key",
        "google_api_key": "",
        "groq_api_key": "groq-key",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_provider_factory_uses_gemini_by_default():
    llm = create_synthesis_llm(settings(), gemini_cls=FakeChatModel, groq_cls=FakeChatModel)

    assert llm.kwargs["model"] == "gemini-3.5-flash-lite"
    assert llm.kwargs["google_api_key"] == "gemini-key"


def test_provider_factory_can_select_groq():
    llm = create_synthesis_llm(
        settings(synthesis_llm_provider="groq", synthesis_model="llama-3.3-70b-versatile"),
        gemini_cls=FakeChatModel,
        groq_cls=FakeChatModel,
    )

    assert llm.kwargs["model"] == "llama-3.3-70b-versatile"
    assert llm.kwargs["api_key"] == "groq-key"


def test_provider_factory_rejects_missing_selected_key():
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        create_synthesis_llm(
            settings(synthesis_llm_provider="groq", groq_api_key=""),
            gemini_cls=FakeChatModel,
            groq_cls=FakeChatModel,
        )


class RateLimitError(Exception):
    status_code = 429


def test_gemini_unavailable_message_is_treated_as_transient():
    error = RuntimeError(
        "503 UNAVAILABLE. {'error': {'code': 503, 'message': 'high demand'}}"
    )

    assert _is_transient_provider_error(error) is True


class FakeStructuredRunner:
    def __init__(self):
        self.calls = 0
        self.active = 0
        self.max_active = 0

    async def ainvoke(self, _messages):
        self.calls += 1
        if self.calls == 1:
            raise RateLimitError("slow down")
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0.01)
        self.active -= 1
        return {"ok": True}


class FakeLLM:
    def __init__(self, runner):
        self.runner = runner

    def with_structured_output(self, _schema):
        return self.runner


@pytest.mark.asyncio
async def test_structured_invocation_retries_429_and_limits_concurrency():
    runner = FakeStructuredRunner()
    service = SynthesisLLMService(llm=FakeLLM(runner), max_concurrency=1, retry_delays=(0,))

    results = await asyncio.gather(
        service._invoke_structured(dict, system="s", human="h"),
        service._invoke_structured(dict, system="s", human="h"),
    )

    assert results == [{"ok": True}, {"ok": True}]
    assert runner.calls == 3
    assert runner.max_active == 1
