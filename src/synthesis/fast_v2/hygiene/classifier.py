"""Evidence Hygiene -- deterministic bibliography/boilerplate classifier.

Ported from the validated hygiene spike. **No LLM. No per-paper hardcoding.**

Provenance
----------
The spike's ``hygiene_classifier.py`` source file was not present on disk in
the ``phase123-merge`` worktree. This implementation is written from the
spike's own written specification in ``evidence_hygiene_report.md`` (signals,
weights, caps, threshold, structural gate, boilerplate rules) and is verified
numerically: :func:`score_from_signals` reproduces the recorded
``hygiene_score`` exactly for every recorded signal vector in
``rq1_before_after.json`` / ``rq2_before_after.json``. Those vectors are
checked in as regression fixtures.

Validated result: RQ1 contamination@10 0.4 -> 0.0, RQ2 0.3 -> 0.0, with no
observed false positives in the manually inspected excluded set.

Scope and limits (do not oversell this component)
-------------------------------------------------
* The threshold 8.0 is calibrated only against the Xu2010/Xu2018 corpus plus
  fixtures. It is a reasonable first cut, NOT a calibrated production
  threshold, and NOT a globally validated scientific-paper classifier.
* Hygiene guarantees "not bibliography/boilerplate". It does NOT guarantee
  "high content value" -- low-information table/figure axis dumps pass.
* Ambiguity biases to KEEP.
* Filtering is **query/runtime evidence selection only**. This module never
  mutates or deletes canonical chunks in the database.

Core structural signal
----------------------
A bibliography entry in real PDF-extracted text starts a **new line** with a
citation-index marker immediately followed by an author-name pattern::

    [8] Censor Y and Segal A 2008 Iterative projection...
    29. Davenport, M.A., Duarte, M.F., ...

This structurally distinguishes a reference-list entry from an inline citation
in prose (``...IMRT) [9,16,18,20,67].``), which is mid-line and never followed
by an author-name pattern.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Sequence

from src.synthesis.fast_v2.evidence.models import EvidenceUnit


class HygieneClass(str, Enum):
    scientific_content = "scientific_content"
    reference_like = "reference_like"
    boilerplate = "boilerplate"


# --- Frozen weights / caps / threshold (validated spike values) -------------

WEIGHT_REFERENCE_ENTRY_LINE = 4.0
CAP_REFERENCE_ENTRY_LINES = 8
WEIGHT_BIBLIOGRAPHIC_TERM = 2.0
CAP_BIBLIOGRAPHIC_TERMS = 8
WEIGHT_YEAR_BEYOND_FIRST_TWO = 1.5
FREE_YEARS = 2
WEIGHT_SEQUENTIAL_REFERENCE = 3.0
WEIGHT_REFERENCE_HEADING = 5.0

HYGIENE_REFERENCE_THRESHOLD = 8.0

#: Vocabulary/year/heading signals only contribute when the structural signal
#: is present. A prose paragraph that merely names a journal or a year can
#: never be flagged on vocabulary alone.
MIN_ENTRY_LINES_FOR_GATED_SIGNALS = 2


# --- Regexes ---------------------------------------------------------------

# One author unit: Surname followed by initials, in either journal style
# ("Censor Y", "Schopfer F") or Springer style ("Davenport, M.A.").
_AUTHOR_UNIT = r"[A-Z][A-Za-z'À-ɏ-]+,?\s+(?:[A-Z]\.?){1,3}"

# An arbitrary-length author list joined by commas and/or "and". Generalised
# from the spike's regression fix: the original pattern only matched two
# authors joined by "and", so real comma-joined 3+ author entries
# ("Censor Y, Bortfeld T, Martin B and Trofimov A 2006 ...") scored zero
# matched entry lines and let a bibliography fragment through as
# scientific_content. Comma-separated multi-author citation lists are standard
# across STEM journals -- this is a generic format fix, not a paper-specific
# patch.
_AUTHOR_LIST = rf"{_AUTHOR_UNIT}(?:\s*(?:,|,?\s*and)\s+{_AUTHOR_UNIT})*"

# A reference-list entry line: start of line, an index marker ("[8]" or "29."),
# then an author list.
_REFERENCE_ENTRY_LINE = re.compile(
    rf"^\s*(?:\[(\d{{1,3}})\]|(\d{{1,3}})\.)\s+{_AUTHOR_LIST}",
    re.MULTILINE,
)

_REFERENCE_HEADING = re.compile(
    r"^\s*(?:references|bibliography|references\s+cited)\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)

_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")

#: Generic STEM publishing vocabulary -- not paper-specific.
_BIBLIOGRAPHIC_TERMS = (
    "ieee trans",
    "inverse probl",
    "j. optim",
    "j. math",
    "siam j",
    "numer. algorithms",
    "math. program",
    "phys. med. biol",
    "springer",
    "elsevier",
    "academic press",
    "university press",
    "vol.",
    "pp.",
    "doi",
    "arxiv",
    "preprint",
    "proc.",
    "proceedings of",
    "ann.",
    "appl.",
    "comput.",
    "optim.",
    "signal process",
)

#: Orthogonal boilerplate class: download/copyright/navigation furniture.
_BOILERPLATE_PHRASES = (
    "downloaded from",
    "ip address",
    "terms and conditions",
    "journal homepage",
    "table of contents",
    "all rights reserved",
    "this content was downloaded",
    "view the article online",
    "for more information",
    "please note that",
    "subscription",
    "sign in",
)


@dataclass(frozen=True)
class HygieneResult:
    hygiene_class: HygieneClass
    hygiene_score: float
    hygiene_signals: dict[str, Any] = field(default_factory=dict)

    @property
    def is_usable_evidence(self) -> bool:
        return self.hygiene_class is HygieneClass.scientific_content


def extract_signals(text: str) -> dict[str, Any]:
    """Compute the raw deterministic signals for one chunk of text."""
    body = text or ""
    lines = [line for line in body.splitlines() if line.strip()]

    indices: list[int] = []
    for match in _REFERENCE_ENTRY_LINE.finditer(body):
        raw = match.group(1) or match.group(2)
        try:
            indices.append(int(raw))
        except (TypeError, ValueError):
            continue

    entry_lines = len(indices)

    # Real bibliographies have runs of consecutive entry indices.
    sequential = sum(
        1 for a, b in zip(indices, indices[1:]) if b == a + 1
    )

    lowered = body.lower()
    bibliographic_terms = sum(1 for term in _BIBLIOGRAPHIC_TERMS if term in lowered)
    boilerplate_hits = sum(1 for phrase in _BOILERPLATE_PHRASES if phrase in lowered)

    return {
        "reference_entry_lines": entry_lines,
        "reference_entry_ratio": round(entry_lines / len(lines), 3) if lines else 0.0,
        "year_count": len(_YEAR.findall(body)),
        "bibliographic_term_count": bibliographic_terms,
        "sequential_reference_count": sequential,
        "reference_heading_present": bool(_REFERENCE_HEADING.search(body)),
        "boilerplate_hits": boilerplate_hits,
    }


def score_from_signals(signals: dict[str, Any]) -> float:
    """Frozen weighted score for the reference_like decision.

    Reproduces the validated spike's ``hygiene_score`` exactly. The structural
    gate is applied here: without at least
    ``MIN_ENTRY_LINES_FOR_GATED_SIGNALS`` reference entry lines, only the
    heading signal may contribute (and 5.0 alone stays under the 8.0
    threshold, so a bare heading never flags a chunk on its own).
    """
    entry_lines = int(signals.get("reference_entry_lines", 0) or 0)
    gated = entry_lines >= MIN_ENTRY_LINES_FOR_GATED_SIGNALS

    score = min(entry_lines, CAP_REFERENCE_ENTRY_LINES) * WEIGHT_REFERENCE_ENTRY_LINE
    score += int(signals.get("sequential_reference_count", 0) or 0) * WEIGHT_SEQUENTIAL_REFERENCE

    if signals.get("reference_heading_present"):
        score += WEIGHT_REFERENCE_HEADING

    if gated:
        terms = int(signals.get("bibliographic_term_count", 0) or 0)
        score += min(terms, CAP_BIBLIOGRAPHIC_TERMS) * WEIGHT_BIBLIOGRAPHIC_TERM
        years = int(signals.get("year_count", 0) or 0)
        score += max(0, years - FREE_YEARS) * WEIGHT_YEAR_BEYOND_FIRST_TWO

    return float(score)


def classify_text(text: str) -> HygieneResult:
    """Classify one chunk as scientific_content / reference_like / boilerplate.

    Bias: ambiguity defaults to KEEP (``scientific_content``).
    """
    signals = extract_signals(text)
    reference_score = score_from_signals(signals)

    if reference_score >= HYGIENE_REFERENCE_THRESHOLD:
        return HygieneResult(HygieneClass.reference_like, reference_score, signals)

    boilerplate_hits = int(signals.get("boilerplate_hits", 0) or 0)
    if boilerplate_hits >= 1:
        # The spike recorded hygiene_score == boilerplate_hits for this class.
        return HygieneResult(HygieneClass.boilerplate, float(boilerplate_hits), signals)

    return HygieneResult(HygieneClass.scientific_content, reference_score, signals)


def classify_evidence_unit(unit: EvidenceUnit) -> EvidenceUnit:
    """Return a copy of ``unit`` carrying hygiene diagnostics.

    Never mutates the input.
    """
    result = classify_text(unit.text)
    return unit.with_hygiene(
        hygiene_class=result.hygiene_class.value,
        hygiene_score=result.hygiene_score,
        hygiene_signals=result.hygiene_signals,
    )


def filter_evidence_units(
    units: Iterable[EvidenceUnit],
) -> tuple[list[EvidenceUnit], list[EvidenceUnit]]:
    """Split units into (kept, dropped), both carrying hygiene diagnostics.

    This is runtime evidence selection. Canonical chunks in the database are
    never mutated or deleted.
    """
    kept: list[EvidenceUnit] = []
    dropped: list[EvidenceUnit] = []
    for unit in units:
        classified = classify_evidence_unit(unit)
        if classified.hygiene_class == HygieneClass.scientific_content.value:
            kept.append(classified)
        else:
            dropped.append(classified)
    return kept, dropped


def contamination_at_k(units: Sequence[EvidenceUnit], k: int = 10) -> float:
    """Diagnostic: fraction of the top-k that is not scientific_content."""
    top = list(units)[:k]
    if not top:
        return 0.0
    bad = sum(
        1
        for unit in top
        if classify_evidence_unit(unit).hygiene_class != HygieneClass.scientific_content.value
    )
    return bad / len(top)
