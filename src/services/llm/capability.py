"""What each task needs from a model, declared instead of discovered.

Every one of the synthesis steps goes through a structured-output call, yet
nothing said so. The adapter therefore had to find out at run time: it built six
candidate runners per call -- three structured-output methods, a prompt-based
JSON fallback, and two hardcoded cross-provider clients -- and tried them in
turn, paying for each attempt.

Stating the requirement up front removes the guessing, and lets the router
refuse a fallback that would answer but not honour the schema. Falling back to a
model that cannot produce the requested structure is the same failure as falling
back to random embeddings: nothing crashes and the output is wrong.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LLMCapability:
    json_schema: bool = False
    min_context: int = 8_000
    tool_calling: bool = False

    def satisfied_by(self, profile) -> tuple[bool, str]:
        """Return whether a model qualifies, and if not, why.

        The reason travels into the selection log so an operator can see which
        providers were skipped and on what grounds, rather than inferring it
        from a bill.
        """
        if self.json_schema and not (profile.supports_json_schema or profile.supports_json_mode):
            return False, "no structured-output support"
        if self.tool_calling and not profile.supports_tool_calling:
            return False, "no tool-calling support"
        if profile.context_window < self.min_context:
            return False, f"context window {profile.context_window} < {self.min_context} required"
        return True, ""


# Every task that reaches an LLM. A task not listed here is a task whose
# requirements nobody has thought about, so get_llm refuses it rather than
# applying a default that may be wrong.
#
# min_context values are starting points sized from the prompts these steps
# actually build -- evidence extraction carries whole page windows. They should
# be revisited against logged prompt lengths rather than left as guesses.
TASK_REGISTRY: dict[str, LLMCapability] = {
    # ---- Synthesis: every step returns a Pydantic schema ----
    "extract_evidence": LLMCapability(json_schema=True, min_context=32_000),
    "extract_paper_evidence_batch": LLMCapability(json_schema=True, min_context=64_000),
    "propose_claims": LLMCapability(json_schema=True, min_context=32_000),
    "verify_entailment": LLMCapability(json_schema=True, min_context=8_000),
    "verify_claim_set": LLMCapability(json_schema=True, min_context=32_000),
    "verify_claim_set_batch": LLMCapability(json_schema=True, min_context=64_000),
    "build_outline": LLMCapability(json_schema=True, min_context=32_000),
    "draft_section": LLMCapability(json_schema=True, min_context=32_000),
    "refine_section": LLMCapability(json_schema=True, min_context=32_000),
    "qa_review_batch": LLMCapability(json_schema=True, min_context=32_000),
    "deduplicate_evidence_batch": LLMCapability(json_schema=True, min_context=32_000),

    # ---- SLR swarm ----
    "generate_criteria": LLMCapability(json_schema=True, min_context=8_000),
    "extract_pico": LLMCapability(json_schema=True, min_context=8_000),
    "optimize_scope": LLMCapability(json_schema=True, min_context=8_000),
    "find_gaps": LLMCapability(json_schema=True, min_context=32_000),
    "screen_paper": LLMCapability(json_schema=True, min_context=8_000),

    # ---- Search and projects ----
    "generate_keywords": LLMCapability(json_schema=True, min_context=8_000),
    "generate_search_strategy": LLMCapability(json_schema=True, min_context=8_000),

    # ---- Offline tooling (not called from any live request path) ----
    # One-off dataset generation for Module 1's NLI cross-encoder fine-tuning
    # (scripts/finetune_nli/01_generate_dataset.py). Still goes through the
    # router rather than a hand-rolled client, per this file's own reason for
    # existing -- an offline script is not exempt from the "5 different
    # cascades" failure mode this registry was built to prevent.
    "generate_nli_training_triplet": LLMCapability(json_schema=True, min_context=8_000),

    # ---- Free-form ----
    "rag_chat": LLMCapability(json_schema=False, min_context=32_000),
    "eval_judge": LLMCapability(json_schema=False, min_context=32_000),
    # Prompt can carry a paper's entire extracted full text (up to ~200k chars).
    "paper_summary": LLMCapability(json_schema=False, min_context=128_000),
}


class UnknownTaskError(RuntimeError):
    """A task asked for an LLM without declaring what it needs."""


def get_capability(task: str) -> LLMCapability:
    capability = TASK_REGISTRY.get(task)
    if capability is None:
        raise UnknownTaskError(
            f"Task {task!r} is not declared in TASK_REGISTRY "
            "(src/services/llm/capability.py). Add it with the context size and "
            "structured-output support it needs -- a task with no stated "
            "requirements cannot be routed safely."
        )
    return capability
