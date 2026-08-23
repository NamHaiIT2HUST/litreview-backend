"""Tests for RemoteOpenScholarGenerator -- fully mocked HTTP client, no
network, no torch/vllm import."""
from __future__ import annotations

import uuid
import json

import pytest

from src.synthesis.fast_v2.evidence.bank import GroundedEvidenceBank
from src.synthesis.fast_v2.evidence.models import EvidenceUnit
from src.synthesis.fast_v2.generator.remote_openscholar import (
    FastV2GenerationError,
    RemoteOpenScholarGenerator,
)

VALID_RESPONSE = {
    "text": json.dumps({
        "claims": [{
            "facet": "D1",
            "is_comparative": False,
            "statements": [{
                "claim_text": "body text",
                "paper_id": "11111111-1111-1111-1111-111111111111",
                "supports": [{"evidence_id": "ev-fixture"}],
            }],
        }],
    }),
    "input_tokens": 3974,
    "output_tokens": 493,
    "generation_ms": 27180.0,
    "finish_reason": "stop",
    "stop_reason": "[Response_End]",
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
    """Records every call so tests can assert on the exact request made."""

    def __init__(self, *, get_response=None, post_response=None, get_exc=None, post_exc=None):
        self._get_response = get_response
        self._post_response = post_response
        self._get_exc = get_exc
        self._post_exc = post_exc
        self.get_calls: list[str] = []
        self.post_calls: list[tuple[str, dict]] = []

    def get(self, url):
        self.get_calls.append(url)
        if self._get_exc:
            raise self._get_exc
        return self._get_response

    def post(self, url, json):
        self.post_calls.append((url, json))
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
    return RemoteOpenScholarGenerator(
        base_url="http://gpu-service:8500", http_client_factory=lambda: client, **kwargs
    )


# --------------------------------------------------------------------------
# Construction / config
# --------------------------------------------------------------------------

def test_construction_requires_base_url():
    with pytest.raises(ValueError):
        RemoteOpenScholarGenerator(base_url="")


def test_min_tokens_must_be_zero():
    with pytest.raises(ValueError):
        RemoteOpenScholarGenerator(base_url="http://x", generation_config={"min_tokens": 450})


def test_frozen_generation_config_defaults():
    gen = RemoteOpenScholarGenerator(base_url="http://x")
    assert gen.generation_config["min_tokens"] == 0
    assert gen.generation_config["stop"] == ["[Response_End]"]
    assert gen.generation_config["stop_token_ids"] == [128009]
    assert gen.generation_config["temperature"] == 0.7
    assert gen.generation_config["max_tokens"] == 3000


# --------------------------------------------------------------------------
# Request payload / one call only
# --------------------------------------------------------------------------

def test_request_payload_matches_frozen_generation_config():
    client = _FakeClient(post_response=_FakeResponse(200, VALID_RESPONSE))
    gen = _make_generator(client)
    gen.generate(question="Q", evidence_bank=_bank())

    assert len(client.post_calls) == 1
    url, payload = client.post_calls[0]
    assert url == "http://gpu-service:8500/generate"
    assert payload["generation_config"]["min_tokens"] == 0
    assert payload["generation_config"]["stop"] == ["[Response_End]"]
    assert payload["generation_config"]["stop_token_ids"] == [128009]
    assert "prompt" in payload and "Q" in payload["prompt"]


def test_exactly_one_generation_request_per_generate_call():
    client = _FakeClient(post_response=_FakeResponse(200, VALID_RESPONSE))
    gen = _make_generator(client)
    draft = gen.generate(question="Q", evidence_bank=_bank())
    assert len(client.post_calls) == 1
    assert draft.generation_calls == 1


# --------------------------------------------------------------------------
# Response mapping
# --------------------------------------------------------------------------

def test_remote_response_mapped_correctly_to_generated_draft():
    client = _FakeClient(post_response=_FakeResponse(200, VALID_RESPONSE))
    gen = _make_generator(client)
    draft = gen.generate(question="Q", evidence_bank=_bank())

    assert draft.text == VALID_RESPONSE["text"]
    assert draft.input_tokens == 3974
    assert draft.output_tokens == 493
    assert draft.finish_reason == "stop"
    assert draft.stop_reason == "[Response_End]"
    assert draft.model_name == "NeuML/Llama-3.1_OpenScholar-8B-AWQ"
    assert draft.generation_ms is not None and draft.generation_ms >= 0
    assert draft.claim_manifest is not None


def test_native_citation_indices_are_extracted_but_not_authoritative():
    """The generator surfaces native indices as diagnostics only -- the
    caller (finalizer) is the actual citation authority, not this adapter."""
    client = _FakeClient(post_response=_FakeResponse(200, VALID_RESPONSE))
    gen = _make_generator(client)
    draft = gen.generate(question="Q", evidence_bank=_bank())
    assert draft.native_citation_indices == ()
    # GeneratedDraft carries no "citations" field at all -- native indices
    # are diagnostics-only by construction, never promoted to citations here.
    assert not hasattr(draft, "citations")


def test_malformed_claim_manifest_fails_closed_without_retry():
    invalid = {**VALID_RESPONSE, "text": "not-json"}
    client = _FakeClient(post_response=_FakeResponse(200, invalid))
    gen = _make_generator(client)
    with pytest.raises(FastV2GenerationError, match="claim manifest"):
        gen.generate(question="Q", evidence_bank=_bank())
    assert len(client.post_calls) == 1


def test_network_and_remote_generation_ms_recorded_separately():
    client = _FakeClient(post_response=_FakeResponse(200, VALID_RESPONSE))
    gen = _make_generator(client)
    gen.generate(question="Q", evidence_bank=_bank())
    assert gen.last_remote_generation_ms == VALID_RESPONSE["generation_ms"]
    assert gen.last_network_ms is not None


# --------------------------------------------------------------------------
# Failure modes -- no silent fallback, always FastV2GenerationError
# --------------------------------------------------------------------------

def test_connection_error_raises_fast_v2_generation_error():
    client = _FakeClient(post_exc=ConnectionError("refused"))
    gen = _make_generator(client)
    with pytest.raises(FastV2GenerationError):
        gen.generate(question="Q", evidence_bank=_bank())


def test_timeout_raises_fast_v2_generation_error():
    class _Timeout(Exception):
        pass

    client = _FakeClient(post_exc=_Timeout("read timed out"))
    gen = _make_generator(client)
    with pytest.raises(FastV2GenerationError):
        gen.generate(question="Q", evidence_bank=_bank())


def test_non_200_response_raises_fast_v2_generation_error():
    client = _FakeClient(post_response=_FakeResponse(500, text="internal error"))
    gen = _make_generator(client)
    with pytest.raises(FastV2GenerationError):
        gen.generate(question="Q", evidence_bank=_bank())


def test_malformed_non_json_response_raises_fast_v2_generation_error():
    client = _FakeClient(post_response=_FakeResponse(200, raise_on_json=True))
    gen = _make_generator(client)
    with pytest.raises(FastV2GenerationError):
        gen.generate(question="Q", evidence_bank=_bank())


def test_response_missing_required_fields_raises_fast_v2_generation_error():
    incomplete = {"text": "hi"}  # missing input_tokens, output_tokens, etc.
    client = _FakeClient(post_response=_FakeResponse(200, incomplete))
    gen = _make_generator(client)
    with pytest.raises(FastV2GenerationError):
        gen.generate(question="Q", evidence_bank=_bank())


def test_unhealthy_server_raises_fast_v2_generation_error():
    client = _FakeClient(get_response=_FakeResponse(503, text="loading"))
    gen = _make_generator(client)
    with pytest.raises(FastV2GenerationError):
        gen.health_check()


def test_health_check_unreachable_raises_fast_v2_generation_error():
    client = _FakeClient(get_exc=ConnectionError("refused"))
    gen = _make_generator(client)
    with pytest.raises(FastV2GenerationError):
        gen.health_check()


def test_healthy_server_returns_health_payload():
    client = _FakeClient(get_response=_FakeResponse(200, {"status": "ok", "loaded": True}))
    gen = _make_generator(client)
    payload = gen.health_check()
    assert payload["status"] == "ok"


def test_failure_never_falls_back_silently():
    """A failed remote call must propagate as an exception -- it must never
    return a fabricated/degraded GeneratedDraft."""
    client = _FakeClient(post_exc=ConnectionError("refused"))
    gen = _make_generator(client)
    with pytest.raises(FastV2GenerationError):
        result = gen.generate(question="Q", evidence_bank=_bank())
        # if we ever got here without raising, that would BE the silent
        # fallback this test exists to prevent
        assert result is None  # unreachable; the pytest.raises above must fire
