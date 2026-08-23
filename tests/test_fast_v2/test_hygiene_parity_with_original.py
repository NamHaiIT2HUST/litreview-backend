"""Direct parity check: fast_v2 hygiene classifier vs the recovered ORIGINAL.

Imports the literal recovered original module from
``scratch/original_dimension_v1_reference/evidence_hygiene/hygiene_classifier.py``
(read-only reference, never modified) and asserts fast_v2's ``classify_text``
reproduces the same class + score for every recorded fixture text this
session recovered: the hygiene spike's own RQ1/RQ2 excluded/kept previews.

This test is skipped (not failed) if the scratch reference directory is not
present -- it is a local recovery artifact, not something every checkout is
expected to have.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ORIGINAL_PATH = (
    REPO_ROOT
    / "scratch"
    / "original_dimension_v1_reference"
    / "evidence_hygiene"
    / "hygiene_classifier.py"
)

pytestmark = pytest.mark.skipif(
    not ORIGINAL_PATH.is_file(),
    reason="recovered ORIGINAL hygiene_classifier.py not present under scratch/",
)


def _load_original_module():
    spec = importlib.util.spec_from_file_location("original_hygiene_classifier", ORIGINAL_PATH)
    module = importlib.util.module_from_spec(spec)
    # Register before exec: Python 3.12's dataclasses resolves string-annotated
    # fields via sys.modules[cls.__module__], which is None if the module was
    # never registered -- AttributeError on the module's own @dataclass classes.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _fixture_cases():
    fixtures_path = Path(__file__).parent / "fixtures" / "hygiene_spike_fixtures.json"
    data = json.loads(fixtures_path.read_text(encoding="utf-8"))
    cases = []
    for i, case in enumerate(data.get("excluded_texts", [])):
        cases.append(pytest.param(
            case["text"], case["expected_class"], id=f"excluded-{case['paper']}-p{case['page']}-{i}"
        ))
    for i, case in enumerate(data.get("kept_texts", [])):
        cases.append(pytest.param(
            case["text"], "scientific_content", id=f"kept-{case['paper']}-p{case['page']}-{i}"
        ))
    return cases


@pytest.mark.parametrize("text,expected_class", _fixture_cases())
def test_fast_v2_matches_original_on_recorded_fixtures(text, expected_class):
    from src.synthesis.fast_v2.hygiene.classifier import classify_text as fast_v2_classify

    original = _load_original_module()
    original_result = original.classify_evidence_unit(text)
    fast_v2_result = fast_v2_classify(text)

    assert fast_v2_result.hygiene_class.value == original_result.hygiene_class, (
        f"class mismatch: original={original_result.hygiene_class!r} "
        f"fast_v2={fast_v2_result.hygiene_class.value!r}"
    )
    assert fast_v2_result.hygiene_score == pytest.approx(original_result.hygiene_score), (
        f"score mismatch: original={original_result.hygiene_score} "
        f"fast_v2={fast_v2_result.hygiene_score}"
    )
    assert fast_v2_result.hygiene_signals == original_result.hygiene_signals


def test_original_reference_module_is_importable_and_unmodified():
    """Sanity: the recovered file still has the exact recorded threshold/weights."""
    original = _load_original_module()
    assert original.classify_evidence_unit(
        "References\n[18] Qu B and Xiu N 2005 A note Inverse Problems 21 1655\n"
        "[19] Rockafellar R T 1970 Convex Analysis Princeton\n"
        "[20] Schopfer F 2008 An iterative method Inverse Problems 24 1\n"
    ).hygiene_class == "reference_like"
