"""OpenScholar generation adapter.

**Lazy by construction.** Importing this module and constructing the adapter
must never load an 8B model -- production, CI, and developer machines may have
no GPU. ``vllm`` and ``torch`` are imported inside :meth:`OpenScholarGenerator.load`
only. Unit tests use ``FakeSynthesisGenerator`` instead.

Validated external runtime result (recorded, not re-verified here)
-----------------------------------------------------------------
Colab T4, ``NeuML/Llama-3.1_OpenScholar-8B-AWQ``:

* warm generation **27.18s**
* input tokens **3974**, output tokens **493**
* ``finish_reason=stop``, ``stop_reason=[Response_End]``

An earlier 162.99s / 3000-token run was **INVALID as latency evidence**: the
model had already emitted ``[Response_End]`` and then repeated numeric output
until ``max_tokens``. That run used ``min_tokens=450``.

**Never reintroduce ``min_tokens=450``.**

Quality caveat: generation *latency* is validated. Final factual grounding is
NOT. Observed generator issues include unsupported claims, overclaiming
future-work language, weak comparison of convergence assumptions, and native
citation misattribution. See the ADR section I.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from src.synthesis.fast_v2.evidence.bank import GroundedEvidenceBank
from src.synthesis.fast_v2.generator.base import FastV2GenerationError, GeneratedDraft
from src.synthesis.fast_v2.generator.prompt import (
    PROMPT_VERSION,
    RESPONSE_END,
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

OPENSCHOLAR_MODEL = "NeuML/Llama-3.1_OpenScholar-8B-AWQ"

#: Frozen, validated generation settings. Changing these invalidates the
#: recorded 27.18s result and risks the runaway-repetition failure mode.
FROZEN_GENERATION_CONFIG: dict[str, Any] = {
    "temperature": 0.7,
    "max_tokens": 3000,
    "min_tokens": 0,
    "stop": [RESPONSE_END],
    "stop_token_ids": [128009],  # Llama-3 <|eot_id|>
}

#: Engine construction settings from the validated Colab run.
FROZEN_ENGINE_CONFIG: dict[str, Any] = {
    "quantization": "awq",
    "dtype": "float16",
    "max_model_len": 16384,
    "enforce_eager": True,
    "disable_custom_all_reduce": True,
}


class OpenScholarGenerator:
    """Adapter over a vLLM OpenScholar engine. Loads only when asked to."""

    def __init__(
        self,
        *,
        model_name: str = OPENSCHOLAR_MODEL,
        generation_config: dict[str, Any] | None = None,
        engine_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.model_name = model_name
        self.generation_config = {**FROZEN_GENERATION_CONFIG, **(generation_config or {})}
        self._engine_factory = engine_factory
        self._engine: Any = None

        if self.generation_config.get("min_tokens"):
            raise ValueError(
                "min_tokens must be 0 for fast_v2. A non-zero min_tokens caused "
                "the invalid 162.99s/3000-token run in which the model emitted "
                "[Response_End] and then repeated output until max_tokens."
            )

    @property
    def is_loaded(self) -> bool:
        return self._engine is not None

    def _default_engine_factory(self, model_name: str) -> Any:
        # Imported here, never at module scope -- CPU machines must be able to
        # import this module.
        import torch
        import vllm

        return vllm.LLM(
            model=model_name,
            tokenizer=model_name,
            tokenizer_mode="auto",
            tensor_parallel_size=torch.cuda.device_count(),
            **FROZEN_ENGINE_CONFIG,
        )

    def load(self) -> Any:
        """Explicitly materialise the engine. Expensive; requires a GPU."""
        if self._engine is None:
            factory = self._engine_factory or self._default_engine_factory
            self._engine = factory(self.model_name)
        return self._engine

    def generate(
        self, *, question: str, evidence_bank: GroundedEvidenceBank
    ) -> GeneratedDraft:
        """One generation call from the bank alone. Never retrieves."""
        prompt = build_prompt(
            question=question,
            evidence=evidence_bank.evidence,
            dimensions=evidence_bank.dimensions,
        )
        evidence_handle_mapping = build_evidence_handle_mapping(
            evidence_bank.evidence
        )

        engine = self.load()
        if engine is None:
            raise RuntimeError(
                "OpenScholar engine unavailable. fast_v2 generation requires a "
                "GPU-backed vLLM engine; there is no CPU fallback and no "
                "fabricated answer. Use FakeSynthesisGenerator for CPU tests."
            )

        import vllm  # local import: see load()

        sampling_params = vllm.SamplingParams(**self.generation_config)

        started = time.perf_counter()
        outputs = engine.generate([prompt], sampling_params)
        generation_ms = (time.perf_counter() - started) * 1000.0

        completion = outputs[0].outputs[0]
        text = completion.text

        try:
            claim_manifest = parse_claim_manifest(text)
        except ClaimManifestParseError as exc:
            raise FastV2GenerationError(
                f"Local OpenScholar returned invalid claim manifest: {exc}"
            ) from exc
        try:
            claim_manifest = bind_manifest_evidence_handles(
                claim_manifest,
                evidence_handle_mapping,
            )
        except UnknownEvidenceHandleError as exc:
            raise FastV2GenerationError(
                f"Local OpenScholar returned {exc}"
            ) from exc

        return GeneratedDraft(
            text=text,
            model_name=self.model_name,
            prompt_version=PROMPT_VERSION,
            generation_calls=1,
            claim_manifest=claim_manifest,
            input_tokens=len(getattr(outputs[0], "prompt_token_ids", []) or []) or None,
            output_tokens=len(getattr(completion, "token_ids", []) or []) or None,
            finish_reason=getattr(completion, "finish_reason", None),
            stop_reason=getattr(completion, "stop_reason", None),
            generation_ms=generation_ms,
            evidence_handle_mapping=evidence_handle_mapping,
            native_citation_indices=extract_native_citation_indices(text),
            generation_config=dict(self.generation_config),
        )
