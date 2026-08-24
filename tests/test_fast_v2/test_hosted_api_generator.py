"""Tests for HostedApiGenerator -- fully mocked HTTP client, no network,
no OpenAI SDK, no torch/vllm import."""
from __future__ import annotations

import uuid

import pytest

from src.synthesis.fast_v2.evidence.bank import GroundedEvidenceBank
from src.synthesis.fast_v2.evidence.models import EvidenceUnit
from src.synthesis.fast_v2.generator.remote_openscholar import FastV2GenerationError
from src.synthesis.fast_v2.generator.hosted_api import HostedApiGenerator

MANIFEST_CONTENT = """{"claims":[{"facet":"D1","is_comparative":false,"statements":[{"claim_text":"body text","paper_id":"11111111-1111-1111-1111-111111111111","supports":[{"evidence_id":"ev-fixture"}]}]}]}"""

VALID_RESPONSE = {
    "id": "chatcmpl-abc123",
    "model": "gpt-4o-mini-2024-07-18",
    "choices": [
        {
            "message": {"content": MANIFEST_CONTENT},
            "finish_reason": "stop",
        }
    ],
    "usage": {"prompt_tokens": 1200, "completion_tokens": 240},
}


class _FakeResponse:
    def __init__(self, status_code=200, json_body=None, text="", raise_on_json=False):
        self.status_code = status_code
        self._json_body = json_body
        self.text = text
        self._raise_on_json = raise_on_json

    def json(self):
        if self._raise_on_json:
            raise ValueError("not JSON")
        return self._json_body


class _FakeClient:
    def __init__(self, *, post_response=None, post_exc=None):
        self._post_response = post_response
        self._post_exc = post_exc
        self.post_calls: list[tuple[str, dict, dict]] = []

    def post(self, url, json, headers=None):
        self.post_calls.append((url, json, headers or {}))
        if self._post_exc:
            raise self._post_exc
        return self._post_response


def _unit():
    return EvidenceUnit.from_chunk(
        paper_id=uuid.uuid4(), title="Paper A", page=1, text="body text",
        source_chunk_id=uuid.uuid4(), page_text_id=uuid.uuid4(),
    ).with_dimension("D1", 1.0)


def _bank():
    return GroundedEvidenceBank.build(
        question="How does X compare to Y?", dimensions=["D1"],
        evidence_by_dimension={"D1": [_unit()]},
    )


def _make_generator(client, **kwargs):
    return HostedApiGenerator(
        base_url="https://api.example.com/v1", api_key="sk-test-key", model="gpt-4o-mini",
        http_client_factory=lambda: client, **kwargs,
    )


# --------------------------------------------------------------------------
# Construction
# --------------------------------------------------------------------------

def test_construction_requires_base_url_key_and_model():
    with pytest.raises(ValueError):
        HostedApiGenerator(base_url="", api_key="k", model="m")
    with pytest.raises(ValueError):
        HostedApiGenerator(base_url="https://x", api_key="", model="m")
    with pytest.raises(ValueError):
        HostedApiGenerator(base_url="https://x", api_key="k", model="")


def test_construction_does_not_open_a_connection():
    gen = HostedApiGenerator(base_url="https://nonexistent.invalid", api_key="k", model="m")
    assert gen.base_url == "https://nonexistent.invalid"


# --------------------------------------------------------------------------
# Request payload / one call only
# --------------------------------------------------------------------------

def test_evidence_prompt_sent_correctly():
    client = _FakeClient(post_response=_FakeResponse(200, VALID_RESPONSE))
    gen = _make_generator(client)
    gen.generate(question="How does X compare to Y?", evidence_bank=_bank())

    _, payload, _ = client.post_calls[0]
    user_message = payload["messages"][1]["content"]
    assert "How does X compare to Y?" in user_message
    assert "body text" in user_message  # evidence content reached the prompt
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["role"] == "user"
    assert payload["response_format"] == {"type": "json_object"}


def test_model_propagated_in_request():
    client = _FakeClient(post_response=_FakeResponse(200, VALID_RESPONSE))
    gen = _make_generator(client)
    gen.generate(question="Q", evidence_bank=_bank())
    _, payload, _ = client.post_calls[0]
    assert payload["model"] == "gpt-4o-mini"


def test_structured_manifest_request_allows_6000_output_tokens():
    client = _FakeClient(post_response=_FakeResponse(200, VALID_RESPONSE))
    gen = _make_generator(client)
    gen.generate(question="Q", evidence_bank=_bank())

    _, payload, _ = client.post_calls[0]
    assert payload["max_tokens"] == 6000


def test_api_key_sent_as_bearer_header():
    client = _FakeClient(post_response=_FakeResponse(200, VALID_RESPONSE))
    gen = _make_generator(client)
    gen.generate(question="Q", evidence_bank=_bank())
    _, _, headers = client.post_calls[0]
    assert headers["Authorization"] == "Bearer sk-test-key"


def test_exactly_one_request():
    client = _FakeClient(post_response=_FakeResponse(200, VALID_RESPONSE))
    gen = _make_generator(client)
    draft = gen.generate(question="Q", evidence_bank=_bank())
    assert len(client.post_calls) == 1
    assert draft.generation_calls == 1


def test_endpoint_is_chat_completions():
    client = _FakeClient(post_response=_FakeResponse(200, VALID_RESPONSE))
    gen = _make_generator(client)
    gen.generate(question="Q", evidence_bank=_bank())
    url, _, _ = client.post_calls[0]
    assert url == "https://api.example.com/v1/chat/completions"


# --------------------------------------------------------------------------
# Response mapping
# --------------------------------------------------------------------------

def test_valid_hosted_response_maps_to_generated_draft():
    client = _FakeClient(post_response=_FakeResponse(200, VALID_RESPONSE))
    gen = _make_generator(client)
    draft = gen.generate(question="Q", evidence_bank=_bank())

    assert draft.text == VALID_RESPONSE["choices"][0]["message"]["content"]
    assert draft.input_tokens == 1200
    assert draft.output_tokens == 240
    assert draft.finish_reason == "stop"
    assert draft.model_name == "gpt-4o-mini-2024-07-18"  # provider-reported model
    assert draft.generation_ms is not None and draft.generation_ms >= 0
    assert gen.last_request_id == "chatcmpl-abc123"
    assert draft.claim_manifest is not None
    assert draft.claim_manifest.claims[0].facet == "D1"


def test_malformed_manifest_fails_closed_after_one_request():
    raw_content = '{"claims":[{"facet":"formulation","statements":[{"claim_text":"cut off'
    malformed = {
        "id": "chatcmpl-truncated",
        "model": "openai/gpt-oss-120b",
        "choices": [
            {"message": {"content": raw_content}, "finish_reason": "length"}
        ],
        "usage": {"prompt_tokens": 3997, "completion_tokens": 3000},
    }
    client = _FakeClient(post_response=_FakeResponse(200, malformed))
    gen = _make_generator(client)
    with pytest.raises(FastV2GenerationError, match="claim manifest") as excinfo:
        gen.generate(question="Q", evidence_bank=_bank())

    error = excinfo.value
    assert error.diagnostics == {
        "response_id": "chatcmpl-truncated",
        "provider_model": "openai/gpt-oss-120b",
        "finish_reason": "length",
        "prompt_tokens": 3997,
        "completion_tokens": 3000,
        "generated_content_chars": len(raw_content),
    }
    assert error.raw_generated_content == raw_content
    assert error.to_diagnostic_dict(include_raw_content=True) == {
        **error.diagnostics,
        "raw_generated_content": raw_content,
    }
    normal_log_text = str(error)
    assert "finish_reason='length'" in normal_log_text
    assert "completion_tokens=3000" in normal_log_text
    assert raw_content not in normal_log_text
    assert "sk-test-key" not in normal_log_text
    assert "Authorization" not in normal_log_text
    assert "sk-test-key" not in repr(error.to_diagnostic_dict(include_raw_content=True))
    assert len(client.post_calls) == 1


# --------------------------------------------------------------------------
# Failure modes -- no silent fallback, always FastV2GenerationError
# --------------------------------------------------------------------------

def test_timeout_raises_fast_v2_generation_error():
    class _Timeout(Exception):
        pass

    client = _FakeClient(post_exc=_Timeout("read timed out"))
    gen = _make_generator(client)
    with pytest.raises(FastV2GenerationError):
        gen.generate(question="Q", evidence_bank=_bank())


def test_http_4xx_raises_fast_v2_generation_error():
    client = _FakeClient(post_response=_FakeResponse(401, text="invalid api key"))
    gen = _make_generator(client)
    with pytest.raises(FastV2GenerationError):
        gen.generate(question="Q", evidence_bank=_bank())


def test_http_5xx_raises_fast_v2_generation_error():
    client = _FakeClient(post_response=_FakeResponse(500, text="internal error"))
    gen = _make_generator(client)
    with pytest.raises(FastV2GenerationError):
        gen.generate(question="Q", evidence_bank=_bank())


def test_malformed_non_json_response_raises_fast_v2_generation_error():
    client = _FakeClient(post_response=_FakeResponse(200, raise_on_json=True))
    gen = _make_generator(client)
    with pytest.raises(FastV2GenerationError):
        gen.generate(question="Q", evidence_bank=_bank())


def test_response_missing_choices_raises_fast_v2_generation_error():
    client = _FakeClient(post_response=_FakeResponse(200, {"usage": {}}))
    gen = _make_generator(client)
    with pytest.raises(FastV2GenerationError):
        gen.generate(question="Q", evidence_bank=_bank())


def test_empty_content_raises_fast_v2_generation_error():
    empty_response = {
        "id": "x", "model": "m",
        "choices": [{"message": {"content": ""}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 0},
    }
    client = _FakeClient(post_response=_FakeResponse(200, empty_response))
    gen = _make_generator(client)
    with pytest.raises(FastV2GenerationError):
        gen.generate(question="Q", evidence_bank=_bank())


def test_whitespace_only_content_raises_fast_v2_generation_error():
    ws_response = {
        "id": "x", "model": "m",
        "choices": [{"message": {"content": "   \n  "}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 0},
    }
    client = _FakeClient(post_response=_FakeResponse(200, ws_response))
    gen = _make_generator(client)
    with pytest.raises(FastV2GenerationError):
        gen.generate(question="Q", evidence_bank=_bank())


def test_failure_never_falls_back_silently():
    client = _FakeClient(post_exc=ConnectionError("refused"))
    gen = _make_generator(client)
    with pytest.raises(FastV2GenerationError):
        result = gen.generate(question="Q", evidence_bank=_bank())
        assert result is None  # unreachable


def test_no_automatic_retry_on_failure():
    """A retry would corrupt benchmark latency measurement -- exactly one
    attempt must be made even on failure."""
    client = _FakeClient(post_exc=ConnectionError("refused"))
    gen = _make_generator(client)
    with pytest.raises(FastV2GenerationError):
        gen.generate(question="Q", evidence_bank=_bank())
    assert len(client.post_calls) == 1
