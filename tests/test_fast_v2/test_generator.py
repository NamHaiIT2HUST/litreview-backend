"""Tests 12-16: generator adapter, frozen generation config, CPU safety."""
from __future__ import annotations


import uuid

import pytest

from src.synthesis.fast_v2.evidence.bank import GroundedEvidenceBank
from src.synthesis.fast_v2.evidence.models import EvidenceUnit
from src.synthesis.fast_v2.generator.base import GeneratedDraft, SynthesisGenerator
from src.synthesis.fast_v2.generator.fake import FakeSynthesisGenerator
from src.synthesis.fast_v2.generator.openscholar import (
    FROZEN_GENERATION_CONFIG,
    OPENSCHOLAR_MODEL,
    OpenScholarGenerator,
)
from src.synthesis.fast_v2.generator.prompt import (
    PROMPT_VERSION,
    build_prompt,
    sanitize_internal_citations,
)


def _bank(n=2):
    units = {}
    for i in range(n):
        text = f"Evidence body {i} referencing prior work [27] and [9,16,18]."
        unit = EvidenceUnit.from_chunk(
            paper_id=uuid.uuid4(),
            title=f"Paper {i}",
            page=i + 1,
            text=text,
            source_chunk_id=uuid.uuid4(),
            page_text_id=uuid.uuid4(),
        ).with_dimension("d", 1.0 + i)
        units.setdefault("d", []).append(unit)
    return GroundedEvidenceBank.build(
        question="How do the papers differ?", dimensions=["d"], evidence_by_dimension=units
    )


# --------------------------------------------------------------------------
# Test 15 -- no model load during module import
# --------------------------------------------------------------------------

def test_importing_the_adapter_does_not_load_the_model():
    """Test 15: CI/production machines may have no GPU.

    Asserted structurally rather than via sys.modules, because sys.modules
    would pass vacuously on a machine where vllm is simply not installed.
    """
    import ast
    import inspect

    from src.synthesis.fast_v2.generator import openscholar

    tree = ast.parse(inspect.getsource(openscholar))
    top_level_imports = set()
    for node in tree.body:  # module level only, not nested function bodies
        if isinstance(node, ast.Import):
            top_level_imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            top_level_imports.add(node.module.split(".")[0])

    assert "vllm" not in top_level_imports
    assert "torch" not in top_level_imports
    assert "transformers" not in top_level_imports


def test_the_heavy_imports_live_inside_functions():
    """The lazy imports must actually exist somewhere in the module."""
    import inspect

    from src.synthesis.fast_v2.generator import openscholar

    source = inspect.getsource(openscholar)
    assert "import vllm" in source, "the adapter should still be able to load a real engine"


def test_constructing_the_adapter_does_not_load_the_model():
    generator = OpenScholarGenerator()
    assert generator.is_loaded is False


def test_the_model_identifier_is_configurable_and_frozen_by_default():
    assert OPENSCHOLAR_MODEL == "NeuML/Llama-3.1_OpenScholar-8B-AWQ"
    assert OpenScholarGenerator().model_name == OPENSCHOLAR_MODEL
    assert OpenScholarGenerator(model_name="other/model").model_name == "other/model"


def test_generating_without_a_gpu_backend_fails_loudly_not_silently():
    """A CPU box must get a clear error, never a fabricated answer."""
    generator = OpenScholarGenerator(engine_factory=lambda *_a, **_k: None)
    with pytest.raises(RuntimeError):
        generator.generate(question="q", evidence_bank=_bank())


# --------------------------------------------------------------------------
# Tests 13/14 -- frozen generation settings
# --------------------------------------------------------------------------

def test_stop_string_response_end_is_configured():
    """Test 13."""
    assert FROZEN_GENERATION_CONFIG["stop"] == ["[Response_End]"]


def test_min_tokens_is_zero():
    """Test 14: min_tokens=450 caused the invalid 162.99s/3000-token run."""
    assert FROZEN_GENERATION_CONFIG["min_tokens"] == 0


def test_the_rest_of_the_validated_generation_config_is_frozen():
    assert FROZEN_GENERATION_CONFIG["temperature"] == 0.7
    assert FROZEN_GENERATION_CONFIG["max_tokens"] == 3000
    assert FROZEN_GENERATION_CONFIG["stop_token_ids"] == [128009]


def test_min_tokens_450_is_never_reintroduced():
    assert FROZEN_GENERATION_CONFIG["min_tokens"] != 450


# --------------------------------------------------------------------------
# Test 12 -- generator receives the Evidence Bank only
# --------------------------------------------------------------------------

def test_generator_receives_the_evidence_bank_only():
    """Test 12: the generator never retrieves."""
    generator = FakeSynthesisGenerator()
    bank = _bank()
    generator.generate(question=bank.question, evidence_bank=bank)

    assert generator.calls == 1
    assert generator.last_bank is bank
    # No retrieval-capable collaborator is reachable from the adapter.
    for attr in ("retriever", "vector_store", "db", "session"):
        assert not hasattr(generator, attr)


def test_prompt_is_built_only_from_bank_evidence():
    bank = _bank()
    prompt = build_prompt(question=bank.question, evidence=bank.evidence)
    for unit in bank.evidence:
        assert unit.title in prompt
    assert bank.question in prompt


def test_exactly_one_generation_call_per_synthesis():
    generator = FakeSynthesisGenerator()
    bank = _bank()
    generator.generate(question=bank.question, evidence_bank=bank)
    assert generator.calls == 1


# --------------------------------------------------------------------------
# Test 16 -- fake generator works on CPU
# --------------------------------------------------------------------------

def test_fake_generator_returns_a_generated_draft():
    """Test 16."""
    bank = _bank()
    draft = FakeSynthesisGenerator().generate(question=bank.question, evidence_bank=bank)
    assert isinstance(draft, GeneratedDraft)
    assert draft.text
    assert draft.generation_calls == 1
    assert draft.claim_manifest is not None
    assert draft.claim_manifest.claims


def test_fake_generator_satisfies_the_generator_interface():
    assert isinstance(FakeSynthesisGenerator(), SynthesisGenerator)


def test_openscholar_generator_satisfies_the_generator_interface():
    assert isinstance(OpenScholarGenerator(), SynthesisGenerator)


# --------------------------------------------------------------------------
# Structured prompt p165_structured_claim_manifest_v1
# --------------------------------------------------------------------------

def test_prompt_version_names_structured_claim_contract():
    assert PROMPT_VERSION == "p165_structured_claim_manifest_v1"


def test_prompt_uses_stable_evidence_and_paper_ids_not_temporary_indices():
    bank = _bank(3)
    prompt = build_prompt(question=bank.question, evidence=bank.evidence)
    for unit in bank.evidence:
        assert unit.evidence_id in prompt
        assert str(unit.paper_id) in prompt
    assert "[0] through" not in prompt


def test_prompt_restricts_the_model_to_the_provided_references():
    prompt = build_prompt(question="q", evidence=_bank().evidence)
    assert "Use only the provided EvidenceUnits" in prompt
    assert "Do not use outside knowledge" in prompt
    assert "Omit claims lacking exact support" in prompt


def test_prompt_requires_json_without_legacy_response_markers():
    prompt = build_prompt(question="q", evidence=_bank().evidence)
    assert "Return exactly one JSON object" in prompt
    assert "[Response_Start]" not in prompt
    assert "[Response_End]" not in prompt


def test_raw_pdf_citation_markers_are_sanitized_out_of_the_index_namespace():
    """Raw '[27]' inside source text must not collide with reference indices."""
    assert sanitize_internal_citations("prior work [27] shows") == "prior work (source-ref 27) shows"
    assert sanitize_internal_citations("see [9,16,18]") == "see (source-ref 9,16,18)"
    assert sanitize_internal_citations("range [7-9]") == "range (source-ref 7-9)"


def test_prompt_preserves_raw_evidence_for_exact_quote_validation():
    prompt = build_prompt(question="q", evidence=_bank().evidence)
    assert "[27]" in prompt
    assert "(source-ref 27)" not in prompt


def test_prompt_is_deterministic():
    bank = _bank()
    assert build_prompt(question="q", evidence=bank.evidence) == build_prompt(
        question="q", evidence=bank.evidence
    )
