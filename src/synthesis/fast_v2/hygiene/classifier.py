"""Evidence Hygiene -- deterministic bibliography/boilerplate classifier.

Literal port from the validated hygiene spike. **No LLM. No per-paper
hardcoding.**

Provenance
----------
The spike's ``hygiene_classifier.py`` source has been recovered from the
session scratch directory that produced it and is checked in as a read-only
reference under ``scratch/original_dimension_v1_reference/evidence_hygiene/
hygiene_classifier.py``. A prior version of this module was an independent
reconstruction from ``evidence_hygiene_report.md`` written when the literal
source was believed lost; that reconstruction diverged from the original in
several load-bearing ways now that the original is available for direct
comparison:

* boilerplate was checked **after** the reference_like gate instead of
  **before** it (order matters: a chunk that is both boilerplate and
  reference-like scored must classify as boilerplate);
* the entry-line regex was a single combined ``[N]|N.`` pattern with no year
  requirement for the bracket style, where the original requires a nearby
  4-digit year for bracket entries specifically (``_RE_BRACKET_ENTRY``) and
  keeps the numbered-Springer style separate (``_RE_NUMBERED_ENTRY``);
* the year signal used one broad ``\\b(19|20)\\d{2}\\b`` pattern instead of the
  original's two narrower patterns (parenthesized-year and
  bare-year-followed-by-capitalised-word), which undercounts equation/page
  numbers as "years";
* the scoring gate structure differed: the reconstruction added the
  entry-line, sequential-reference and heading weights unconditionally, where
  the original only awards the entry-line/sequential/vocabulary/year
  contributions when ``entry_line_count >= 2`` (the standalone-heading path
  uses a different, smaller bonus, 6.0 vs the gated heading weight 5.0);
* the bibliographic-term and boilerplate-phrase vocabularies were different
  (non-identical) lists.

This module now reproduces the original's ``extract_signals`` / scoring /
classification logic verbatim -- same regexes, same constants, same gating
structure, same check order -- adapted only at the boundary: input is
``EvidenceUnit`` (or raw ``text: str`` for the pure function), output is
``HygieneClass``/``HygieneResult`` matching fast_v2's existing diagnostics
shape (``hygiene_class``, ``hygiene_score``, ``hygiene_signals``).

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
"""
from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.synthesis.fast_v2.evidence.models import EvidenceUnit


class HygieneClass(str, Enum):
    scientific_content = "scientific_content"
    reference_like = "reference_like"
    boilerplate = "boilerplate"


# --- Regexes (verbatim from the original spike) -----------------------------
# Unicode-aware letter class so accented/ligature characters from PDF text
# extraction (e.g. "Trofimov", "Schopfer") don't break matching.
_LETTER = r"[^\W\d_]"
_AUTHOR_SURNAME = rf"{_LETTER}(?:{_LETTER}|-)+"
_AUTHOR_INITIAL = rf"{_LETTER}\.?(?:-{_LETTER}\.?)?"
_AUTHOR_UNIT = rf"{_AUTHOR_SURNAME}\s+{_AUTHOR_INITIAL}"

# "[8] Censor Y and Segal A 2008 ..." / "[20] Schopfer F, Schuster T and Louis A K 2008 ..." /
# "[5] Censor Y, Bortfeld T, Martin B and Trofimov A 2006 ..." (arbitrary-length,
# comma-and/or-"and"-joined author list, ending in a 4-digit year within the
# rest of the line -- multi-line-wrapped titles are handled separately by the
# sequential-reference-count signal, not by this single-line regex).
_RE_BRACKET_ENTRY = re.compile(
    rf"^\[(\d{{1,3}})\]\s+{_AUTHOR_UNIT}(?:(?:,\s*|\s+and\s+){_AUTHOR_UNIT})*.{{0,80}}?\b((?:19|20)\d{{2}})\b"
)
# "29. Davenport, M.A., Duarte, M.F., Eldar, Y.C., Kutyniok, G.: ..." /
# "67. Xu, H.-K.: A variable ..."
_RE_NUMBERED_ENTRY = re.compile(
    rf"^(\d{{1,3}})\.\s+{_AUTHOR_SURNAME},\s*{_LETTER}\.(-?{_LETTER}\.)?"
)

_REFERENCE_HEADING = re.compile(r"^\s*(references|bibliography)\s*$", re.IGNORECASE)

# Generic academic-publishing vocabulary (STEM-wide, not specific to any paper).
_BIBLIOGRAPHIC_TERMS = [
    "ieee trans", "inverse probl", "j. optim", "j. r. stat", "numer. algorithms",
    "numer. funct. anal", "siam j.", "siam rev", "springer", "cambridge university press",
    "oxford university press", "proceedings", "proc.", "vol.", " pp.", "pp ", "doi:",
    "doi.org", "arxiv", "j. math. anal", "stat. comput", "ann. oper. res",
    "phys. med. biol", "med. phys", "neural comput", "j. nonlinear convex anal",
    "math. program", "multiscale model", "j. london math", "j. visual commun",
    "image represent", "acad. press", "elsevier",
]

# Publication-year patterns: parenthesized "(2010)" or a bare "1994 Numer." style
# year followed by a capitalized word (journal-name style), NOT just any 4-digit
# number (avoids counting equation/page numbers as years).
_YEAR_PAREN = re.compile(r"\(((?:19|20)\d{2})\)")
_YEAR_BARE_JOURNAL = re.compile(r"\b((?:19|20)\d{2})\s+[A-Z][a-zA-Z]")

_BOILERPLATE_PHRASES = [
    "downloaded from", "this content was downloaded", "ip address",
    "terms and conditions", "journal homepage", "table of contents",
    "creative commons", "all rights reserved", "unauthorized reproduction",
    "please cite this article as",
]

#: Frozen weights / caps / threshold -- verbatim from the validated spike.
WEIGHT_REFERENCE_ENTRY_LINE = 4.0
CAP_REFERENCE_ENTRY_LINES = 8
WEIGHT_BIBLIOGRAPHIC_TERM = 2.0
CAP_BIBLIOGRAPHIC_TERMS = 8
WEIGHT_YEAR_BEYOND_FIRST_TWO = 1.5
FREE_YEARS = 2
WEIGHT_SEQUENTIAL_REFERENCE = 3.0
WEIGHT_REFERENCE_HEADING_GATED = 5.0
#: Standalone-heading bonus (entry_line_count < 2 but a heading line is
#: present) is a DIFFERENT, smaller constant than the gated heading weight --
#: this asymmetry is in the original and is preserved, not a typo.
WEIGHT_REFERENCE_HEADING_STANDALONE = 6.0

HYGIENE_REFERENCE_THRESHOLD = 8.0

#: Vocabulary/year/heading-gated signals only contribute when the structural
#: entry-line signal is present at all. A prose paragraph that merely names a
#: journal or a year can never be flagged on vocabulary alone.
MIN_ENTRY_LINES_FOR_GATED_SIGNALS = 2


@dataclass(frozen=True)
class HygieneResult:
    hygiene_class: HygieneClass
    hygiene_score: float
    hygiene_signals: dict[str, Any] = field(default_factory=dict)

    @property
    def is_usable_evidence(self) -> bool:
        return self.hygiene_class is HygieneClass.scientific_content


def _match_entry_line(line: str) -> re.Match | None:
    line = line.strip()
    if not line:
        return None
    m = _RE_BRACKET_ENTRY.match(line)
    if m:
        return m
    return _RE_NUMBERED_ENTRY.match(line)


def _sequential_run_count(numbers: list[int]) -> int:
    """Count adjacent pairs (n, n+1) among (sorted, deduped) entry numbers.

    >=2 such adjacent pairs means >=3 consecutive reference indices appeared,
    which real bibliography entries do and coincidental single citation-like
    lines do not.
    """
    uniq_sorted = sorted(set(numbers))
    return sum(1 for a, b in zip(uniq_sorted, uniq_sorted[1:]) if b - a == 1)


def extract_signals(text: str) -> dict[str, Any]:
    """Compute the raw deterministic signals for one chunk of text.

    Verbatim logic from the original spike's ``classify_evidence_unit(text)``,
    split out as its own function purely so fast_v2's existing test shape
    (``extract_signals`` / ``score_from_signals`` / ``classify_text``) keeps
    working -- the computation itself is unchanged.
    """
    body = text or ""
    lines = body.splitlines()
    non_empty_lines = [line for line in lines if line.strip()]
    total_lines = max(len(non_empty_lines), 1)

    entry_numbers: list[int] = []
    entry_line_count = 0
    for line in non_empty_lines:
        m = _match_entry_line(line)
        if m:
            entry_line_count += 1
            try:
                entry_numbers.append(int(m.group(1)))
            except (ValueError, IndexError, TypeError):
                pass

    reference_entry_ratio = entry_line_count / total_lines

    lower_text = body.lower()
    bibliographic_term_count = sum(1 for term in _BIBLIOGRAPHIC_TERMS if term in lower_text)

    year_count = len(_YEAR_PAREN.findall(body)) + len(_YEAR_BARE_JOURNAL.findall(body))

    sequential_reference_count = _sequential_run_count(entry_numbers)

    reference_heading_present = any(_REFERENCE_HEADING.match(line) for line in non_empty_lines)

    boilerplate_hits = sum(1 for phrase in _BOILERPLATE_PHRASES if phrase in lower_text)

    return {
        "reference_entry_lines": entry_line_count,
        "reference_entry_ratio": round(reference_entry_ratio, 3),
        "year_count": year_count,
        "bibliographic_term_count": bibliographic_term_count,
        "sequential_reference_count": sequential_reference_count,
        "reference_heading_present": reference_heading_present,
        "boilerplate_hits": boilerplate_hits,
    }


def score_from_signals(signals: dict[str, Any]) -> float:
    """Frozen weighted score for the reference_like decision.

    Verbatim gating structure from the original spike: the entry-line,
    sequential-reference, vocabulary and year contributions are only added
    when ``reference_entry_lines >= MIN_ENTRY_LINES_FOR_GATED_SIGNALS``. A
    standalone heading line (no gated entry lines) gets a smaller, separate
    bonus instead of the gated heading weight.
    """
    entry_line_count = int(signals.get("reference_entry_lines", 0) or 0)
    reference_heading_present = bool(signals.get("reference_heading_present"))

    score = 0.0
    if entry_line_count >= MIN_ENTRY_LINES_FOR_GATED_SIGNALS:
        bibliographic_term_count = int(signals.get("bibliographic_term_count", 0) or 0)
        year_count = int(signals.get("year_count", 0) or 0)
        sequential_reference_count = int(signals.get("sequential_reference_count", 0) or 0)

        score += WEIGHT_REFERENCE_ENTRY_LINE * min(entry_line_count, CAP_REFERENCE_ENTRY_LINES)
        score += WEIGHT_BIBLIOGRAPHIC_TERM * min(bibliographic_term_count, CAP_BIBLIOGRAPHIC_TERMS)
        score += WEIGHT_YEAR_BEYOND_FIRST_TWO * max(year_count - FREE_YEARS, 0)
        score += WEIGHT_SEQUENTIAL_REFERENCE * sequential_reference_count
        score += WEIGHT_REFERENCE_HEADING_GATED if reference_heading_present else 0.0
    elif reference_heading_present:
        score += WEIGHT_REFERENCE_HEADING_STANDALONE

    return round(score, 2)


def classify_text(text: str) -> HygieneResult:
    """Classify one chunk of raw text.

    Bias: ambiguity defaults to KEEP (``scientific_content``). Boilerplate is
    checked FIRST -- it is orthogonal to bibliography density and visually
    unambiguous when the phrases are present, so a chunk that is both
    boilerplate and reference-scored must classify as boilerplate.
    """
    signals = extract_signals(text)

    boilerplate_hits = int(signals.get("boilerplate_hits", 0) or 0)
    if boilerplate_hits >= 1:
        return HygieneResult(HygieneClass.boilerplate, float(boilerplate_hits), signals)

    score = score_from_signals(signals)
    if score >= HYGIENE_REFERENCE_THRESHOLD:
        return HygieneResult(HygieneClass.reference_like, score, signals)

    return HygieneResult(HygieneClass.scientific_content, score, signals)


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
