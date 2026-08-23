"""CPU-safe fake generator for tests and wiring smoke runs.

Loads nothing and calls nothing. It records how it was invoked so tests can
assert the one-generation-call invariant and the "bank only" invariant.

Deliberately has no ``retriever`` / ``vector_store`` / ``db`` attribute -- a
generator that could retrieve would violate the architecture.
"""
from __future__ import annotations

from src.synthesis.fast_v2.evidence.bank import GroundedEvidenceBank
from src.synthesis.fast_v2.generator.base import GeneratedDraft
from src.synthesis.fast_v2.generator.prompt import (
    PROMPT_VERSION,
    build_prompt,
    extract_native_citation_indices,
)


class FakeSynthesisGenerator:
    """Deterministic stand-in for :class:`OpenScholarGenerator`."""

    def __init__(self, *, text: str | None = None, model_name: str = "fake-generator") -> None:
        self._text = text
        self.model_name = model_name
        self.calls = 0
        self.last_bank: GroundedEvidenceBank | None = None
        self.last_prompt: str | None = None

    def generate(
        self, *, question: str, evidence_bank: GroundedEvidenceBank
    ) -> GeneratedDraft:
        self.calls += 1
        self.last_bank = evidence_bank
        self.last_prompt = build_prompt(question=question, evidence=evidence_bank.evidence)

        if self._text is not None:
            text = self._text
        else:
            indices = "".join(f"[{i}]" for i in range(len(evidence_bank.evidence)))
            text = (
                f"Synthesised answer for: {question} "
                f"Drawing on the supplied references {indices}."
            )

        return GeneratedDraft(
            text=text,
            model_name=self.model_name,
            prompt_version=PROMPT_VERSION,
            generation_calls=1,
            input_tokens=len(self.last_prompt.split()),
            output_tokens=len(text.split()),
            finish_reason="stop",
            stop_reason="[Response_End]",
            generation_ms=0.0,
            native_citation_indices=extract_native_citation_indices(text),
        )
