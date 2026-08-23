"""Generator boundary.

The synthesis service is coupled to this interface, never to vLLM. Swapping
the generator (fake on CPU, OpenScholar on GPU) must not touch the pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from src.synthesis.fast_v2.evidence.bank import GroundedEvidenceBank
from src.synthesis.fast_v2.grounding.manifest import ClaimManifest


class FastV2GenerationError(RuntimeError):
    """Generator transport, response-shape, or manifest-contract failure."""


@dataclass(frozen=True)
class GeneratedDraft:
    """Raw generator output plus its telemetry.

    ``text`` is raw generator output. Production Fast v2 requires it to parse
    into ``claim_manifest``. Any bracket markers in raw output remain
    diagnostics only and are never authoritative provenance.
    """

    text: str
    model_name: str
    prompt_version: str
    generation_calls: int = 1
    claim_manifest: ClaimManifest | None = None

    input_tokens: int | None = None
    output_tokens: int | None = None
    finish_reason: str | None = None
    stop_reason: str | None = None
    generation_ms: float | None = None

    #: Diagnostics only. Never published as final citations.
    native_citation_indices: tuple[int, ...] = ()
    generation_config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "model_name": self.model_name,
            "prompt_version": self.prompt_version,
            "generation_calls": self.generation_calls,
            "claim_manifest": (
                None if self.claim_manifest is None else self.claim_manifest.to_dict()
            ),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "finish_reason": self.finish_reason,
            "stop_reason": self.stop_reason,
            "generation_ms": self.generation_ms,
            "native_citation_indices": list(self.native_citation_indices),
            "generation_config": dict(self.generation_config),
        }


@runtime_checkable
class SynthesisGenerator(Protocol):
    """Produces one draft from a question and an already-built evidence bank.

    Implementations MUST NOT retrieve. The bank is the complete evidence
    input, and exactly one generation call is expected per synthesis.
    """

    def generate(
        self, *, question: str, evidence_bank: GroundedEvidenceBank
    ) -> GeneratedDraft:
        ...
