"""Generic OpenAI-compatible hosted-API generation adapter.

Alternative to ``RemoteOpenScholarGenerator`` for benchmarking Fast v2
generation speed/cost against a pay-per-request hosted LLM API, without
maintaining a persistent GPU. Same ``SynthesisGenerator`` protocol and
structured claim-manifest prompt; this module changes only the wire format and
endpoint of the ONE generation call. It never retrieves.

Deliberately provider-agnostic: a generic ``POST {base_url}/chat/completions``
OpenAI-compatible contract (``messages``, ``choices[0].message.content``,
``usage.prompt_tokens``/``completion_tokens``), not a single hardcoded vendor
SDK. Any OpenAI-compatible endpoint (OpenAI itself, or a compatible proxy/
router) works by pointing ``FAST_V2_HOSTED_API_BASE_URL`` at it.

No official OpenAI SDK dependency -- plain ``httpx``, matching
``remote_openscholar.py``'s existing pattern in this package.

Failure policy: identical to ``RemoteOpenScholarGenerator`` -- every failure
mode raises :class:`FastV2GenerationError` (imported, not redefined, so
callers only ever need to catch one exception type across generators). No
silent fallback to Legacy, OpenScholar, another hosted model, or the fake
generator.
"""
from __future__ import annotations

import time
from typing import Any, Callable

from src.synthesis.fast_v2.evidence.bank import GroundedEvidenceBank
from src.synthesis.fast_v2.generator.base import FastV2GenerationError, GeneratedDraft
from src.synthesis.fast_v2.generator.prompt import (
    PROMPT_VERSION,
    RESPONSE_END,
    build_prompt,
    extract_native_citation_indices,
)
from src.synthesis.fast_v2.grounding.manifest import (
    ClaimManifestParseError,
    parse_claim_manifest,
)

#: Short wrapping role instruction only -- NOT the frozen prompt content.
#: Structured manifest prompt goes entirely into the user message.
SYSTEM_ROLE_INSTRUCTION = (
    "You are an AI research assistant. Follow the user's instructions exactly."
)

#: Structured JSON needs enough room to close the full claim manifest.
STRUCTURED_MANIFEST_MAX_TOKENS = 6000

#: Same temperature/stop as the frozen OpenScholar config
#: (src/synthesis/fast_v2/generator/openscholar.py::FROZEN_GENERATION_CONFIG).
#: min_tokens and stop_token_ids are vLLM-specific and have no OpenAI-
#: compatible equivalent, so they are intentionally omitted here.
DEFAULT_GENERATION_CONFIG: dict[str, Any] = {
    "temperature": 0.7,
    "max_tokens": STRUCTURED_MANIFEST_MAX_TOKENS,
    "stop": [RESPONSE_END],
}


class HostedApiGenerator:
    """OpenAI-compatible chat-completions adapter. Construction never opens
    a connection or validates the API key against the provider."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        generation_config: dict[str, Any] | None = None,
        connect_timeout_s: float = 10.0,
        generation_timeout_s: float = 120.0,
        http_client_factory: Callable[[], Any] | None = None,
    ) -> None:
        missing = [
            name for name, value in (("base_url", base_url), ("api_key", api_key), ("model", model))
            if not value
        ]
        if missing:
            raise ValueError(
                f"HostedApiGenerator requires {', '.join(missing)} to be set. "
                "fast_v2 does not guess a hosted-API provider/model/key."
            )

        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.generation_config = {**DEFAULT_GENERATION_CONFIG, **(generation_config or {})}

        self._connect_timeout_s = connect_timeout_s
        self._generation_timeout_s = generation_timeout_s
        self._http_client_factory = http_client_factory

        # Diagnostics from the most recent generate() call.
        self.last_request_id: str | None = None
        self.last_provider_model: str | None = None

    def _default_http_client_factory(self) -> Any:
        import httpx

        return httpx.Client(
            timeout=httpx.Timeout(
                connect=self._connect_timeout_s,
                read=self._generation_timeout_s,
                write=self._generation_timeout_s,
                pool=self._connect_timeout_s,
            )
        )

    def _get_client(self) -> Any:
        factory = self._http_client_factory or self._default_http_client_factory
        return factory()

    def generate(
        self, *, question: str, evidence_bank: GroundedEvidenceBank
    ) -> GeneratedDraft:
        """One hosted-API generation call from the bank alone. Never retrieves.

        No automatic retry: a retry would corrupt the latency measurement
        this generator exists to produce for benchmarking.
        """
        prompt = build_prompt(
            question=question,
            evidence=evidence_bank.evidence,
            dimensions=evidence_bank.dimensions,
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_ROLE_INSTRUCTION},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            **self.generation_config,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}

        client = self._get_client()
        started = time.perf_counter()
        try:
            response = client.post(
                f"{self.base_url}/chat/completions", json=payload, headers=headers
            )
        except Exception as exc:
            raise FastV2GenerationError(
                f"Hosted API request failed ({self.base_url}/chat/completions): "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        network_ms = (time.perf_counter() - started) * 1000.0

        if response.status_code != 200:
            raise FastV2GenerationError(
                f"Hosted API returned HTTP {response.status_code} from "
                f"{self.base_url}/chat/completions: {response.text[:500]}"
            )

        try:
            data = response.json()
        except Exception as exc:
            raise FastV2GenerationError(
                "Hosted API returned a malformed (non-JSON) response"
            ) from exc

        try:
            choice = data["choices"][0]
            text = choice["message"]["content"]
            finish_reason = choice.get("finish_reason")
        except (KeyError, IndexError, TypeError) as exc:
            raise FastV2GenerationError(
                f"Hosted API response missing expected choices[0].message.content shape; "
                f"got keys {list(data.keys())}"
            ) from exc

        if not (text or "").strip():
            raise FastV2GenerationError(
                "Hosted API returned empty generated content -- refusing to "
                "treat an empty string as a valid draft."
            )

        usage = data.get("usage") or {}
        self.last_request_id = data.get("id")
        self.last_provider_model = data.get("model")
        failure_diagnostics = {
            "response_id": self.last_request_id,
            "provider_model": self.last_provider_model,
            "finish_reason": finish_reason,
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "generated_content_chars": len(text),
        }

        try:
            claim_manifest = parse_claim_manifest(text)
        except ClaimManifestParseError as exc:
            safe_metadata = ", ".join(
                f"{name}={value!r}" for name, value in failure_diagnostics.items()
            )
            raise FastV2GenerationError(
                f"Hosted API returned invalid structured claim manifest: {exc} "
                f"({safe_metadata})",
                diagnostics=failure_diagnostics,
                raw_generated_content=text,
            ) from exc

        return GeneratedDraft(
            text=text,
            model_name=self.last_provider_model or self.model,
            prompt_version=PROMPT_VERSION,
            generation_calls=1,
            claim_manifest=claim_manifest,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            finish_reason=finish_reason,
            stop_reason=None,  # no vLLM-style stop_reason in the OpenAI-compatible contract
            generation_ms=network_ms,
            native_citation_indices=extract_native_citation_indices(text),
            generation_config=dict(self.generation_config),
        )
