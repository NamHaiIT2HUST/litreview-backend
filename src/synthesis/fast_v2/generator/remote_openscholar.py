"""Remote OpenScholar generation adapter -- HTTP boundary to a warm GPU service.

**Never imports vllm/torch.** This is the piece that lets the CPU-only P-165
backend call OpenScholar without loading an 8B model in-process: the model
lives in a separate warm GPU service (see
``scripts/fast_v2_openscholar_gpu_service.py``) reached over HTTP.
``OpenScholarGenerator`` (in-process vLLM) is a different adapter for when the
backend itself runs on the GPU box; this module is for the split-process
deployment.

Same frozen generation config as the validated local run
(``src/synthesis/fast_v2/generator/openscholar.py``), same structured
claim-manifest prompt, same ``SynthesisGenerator`` protocol.
Retrieval never happens here -- the caller's ``GroundedEvidenceBank`` is the
only evidence input.

Failure policy: any service problem (unreachable, timeout, unhealthy,
malformed response) raises :class:`FastV2GenerationError`. There is no silent
fallback to Legacy or another model -- that would hide a latency/cost change
behind what looks like a normal Fast v2 response.
"""
from __future__ import annotations

import time
from typing import Any, Callable

from src.synthesis.fast_v2.evidence.bank import GroundedEvidenceBank
from src.synthesis.fast_v2.generator.base import FastV2GenerationError, GeneratedDraft
from src.synthesis.fast_v2.generator.openscholar import (
    FROZEN_GENERATION_CONFIG,
    OPENSCHOLAR_MODEL,
)
from src.synthesis.fast_v2.generator.prompt import (
    PROMPT_VERSION,
    UnknownEvidenceHandleError,
    bind_manifest_evidence_handles,
    build_evidence_handle_mapping,
    build_prompt,
    extract_native_citation_indices,
)
from src.synthesis.fast_v2.grounding.manifest import (
    ClaimManifestParseError,
    parse_claim_manifest,
)

#: Response fields the GPU service contract guarantees. A response missing
#: any of these is treated as malformed, not partially trusted.
REQUIRED_RESPONSE_FIELDS = (
    "text",
    "input_tokens",
    "output_tokens",
    "generation_ms",
    "finish_reason",
    "stop_reason",
)


class RemoteOpenScholarGenerator:
    """HTTP adapter to a warm OpenScholar GPU service. Same protocol as the
    in-process generators; construction never touches the network."""

    def __init__(
        self,
        *,
        base_url: str,
        model_name: str = OPENSCHOLAR_MODEL,
        generation_config: dict[str, Any] | None = None,
        connect_timeout_s: float = 10.0,
        generation_timeout_s: float = 120.0,
        http_client_factory: Callable[[], Any] | None = None,
    ) -> None:
        if not base_url:
            raise ValueError(
                "RemoteOpenScholarGenerator requires a non-empty base_url. "
                "fast_v2 does not guess a GPU service endpoint."
            )
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.generation_config = {**FROZEN_GENERATION_CONFIG, **(generation_config or {})}

        if self.generation_config.get("min_tokens"):
            raise ValueError(
                "min_tokens must be 0 for fast_v2. A non-zero min_tokens caused "
                "the invalid 162.99s/3000-token run in which the model emitted "
                "[Response_End] and then repeated output until max_tokens."
            )

        self._connect_timeout_s = connect_timeout_s
        self._generation_timeout_s = generation_timeout_s
        self._http_client_factory = http_client_factory

        # Diagnostics from the most recent generate() call -- see module
        # docstring / observability requirement: network overhead vs the
        # service's own reported generation time are recorded separately.
        self.last_network_ms: float | None = None
        self.last_remote_generation_ms: float | None = None

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

    def health_check(self) -> dict[str, Any]:
        """GET /health. Raises FastV2GenerationError if unreachable/unhealthy."""
        client = self._get_client()
        try:
            response = client.get(f"{self.base_url}/health")
        except Exception as exc:  # connection error, timeout, DNS, etc.
            raise FastV2GenerationError(
                f"OpenScholar GPU service unreachable at {self.base_url}: {exc}"
            ) from exc

        if response.status_code != 200:
            raise FastV2GenerationError(
                f"OpenScholar GPU service unhealthy: HTTP {response.status_code} "
                f"from {self.base_url}/health"
            )
        try:
            return response.json()
        except Exception as exc:
            raise FastV2GenerationError(
                f"OpenScholar GPU service /health returned a malformed (non-JSON) response"
            ) from exc

    def generate(
        self, *, question: str, evidence_bank: GroundedEvidenceBank
    ) -> GeneratedDraft:
        """One remote generation call from the bank alone. Never retrieves."""
        prompt = build_prompt(
            question=question,
            evidence=evidence_bank.evidence,
            dimensions=evidence_bank.dimensions,
        )
        evidence_handle_mapping = build_evidence_handle_mapping(
            evidence_bank.evidence
        )
        payload = {"prompt": prompt, "generation_config": dict(self.generation_config)}

        client = self._get_client()
        started = time.perf_counter()
        try:
            response = client.post(f"{self.base_url}/generate", json=payload)
        except Exception as exc:
            raise FastV2GenerationError(
                f"OpenScholar GPU service request failed ({self.base_url}/generate): "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        network_ms = (time.perf_counter() - started) * 1000.0

        if response.status_code != 200:
            raise FastV2GenerationError(
                f"OpenScholar GPU service returned HTTP {response.status_code} "
                f"from {self.base_url}/generate: {response.text[:500]}"
            )

        try:
            data = response.json()
        except Exception as exc:
            raise FastV2GenerationError(
                "OpenScholar GPU service returned a malformed (non-JSON) response"
            ) from exc

        missing = [field for field in REQUIRED_RESPONSE_FIELDS if field not in data]
        if missing:
            raise FastV2GenerationError(
                f"OpenScholar GPU service response missing required fields {missing}; "
                f"got keys {list(data.keys())}"
            )

        text = data["text"]
        remote_generation_ms = data.get("generation_ms")
        self.last_network_ms = round(network_ms - (remote_generation_ms or 0.0), 3)
        self.last_remote_generation_ms = remote_generation_ms

        try:
            claim_manifest = parse_claim_manifest(text)
        except ClaimManifestParseError as exc:
            raise FastV2GenerationError(
                f"OpenScholar GPU service returned invalid claim manifest: {exc}"
            ) from exc
        try:
            claim_manifest = bind_manifest_evidence_handles(
                claim_manifest,
                evidence_handle_mapping,
            )
        except UnknownEvidenceHandleError as exc:
            raise FastV2GenerationError(
                f"OpenScholar GPU service returned {exc}"
            ) from exc

        return GeneratedDraft(
            text=text,
            model_name=self.model_name,
            prompt_version=PROMPT_VERSION,
            generation_calls=1,
            claim_manifest=claim_manifest,
            input_tokens=data.get("input_tokens"),
            output_tokens=data.get("output_tokens"),
            finish_reason=data.get("finish_reason"),
            stop_reason=data.get("stop_reason"),
            generation_ms=network_ms,  # total wall time of the HTTP round trip
            evidence_handle_mapping=evidence_handle_mapping,
            native_citation_indices=extract_native_citation_indices(text),
            generation_config=dict(self.generation_config),
        )
