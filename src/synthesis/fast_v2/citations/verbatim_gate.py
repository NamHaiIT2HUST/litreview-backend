"""Deterministic verbatim/near-verbatim copying detector, formalized from
the audit script ``scratch/audit_verbatim_overlap.py``.

For every factual/technical claim span that received a citation handle, find
the longest contiguous run of shared words between the claim's own text and
the text of the evidence unit(s) it cites. A long contiguous run is a strong
signal of near-verbatim copying (genuine paraphrase essentially never
reproduces 8+ consecutive words by chance) -- but a long run of DIGITS
(confidence intervals, relative risks, percentages) is legitimate exact
quantitative reporting, not prose plagiarism, and must not be flagged the
same way.

No LLM call. Read-only. Makes no change to any text.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from src.synthesis.fast_v2.citations.anthropic_citations import (
    is_substantive_prose,
    split_paragraph_into_spans,
)
from src.synthesis.fast_v2.citations.unsupported_gate import (
    FACTUAL_TECHNICAL,
    classify_span_type,
    extract_span_citations,
)

VERBATIM_RISK = "VERBATIM_RISK"
NUMERIC_LEGITIMATE = "NUMERIC_LEGITIMATE"
CLEAN = "CLEAN"

#: A contiguous run of this many shared words or more is flagged. Below this
#: length, overlap is ordinary shared terminology/phrasing, not copying.
MIN_RUN_WORDS = 8

#: If more than this fraction of the matched run's words contain a digit,
#: the run is numeric/statistical content (RR, CI, %, counts) being
#: reported exactly -- expected and correct, not flagged as prose copying.
NUMERIC_RUN_DIGIT_RATIO = 0.4

_WORD_RE = re.compile(r"[A-Za-z0-9']+")


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def _longest_common_run(a_words: Sequence[str], b_words: Sequence[str]) -> tuple[int, list[str]]:
    sm = SequenceMatcher(a=a_words, b=b_words, autojunk=False)
    match = sm.find_longest_match(0, len(a_words), 0, len(b_words))
    return match.size, list(a_words[match.a:match.a + match.size])


def _is_numeric_run(words: Sequence[str]) -> bool:
    if not words:
        return False
    digit_words = sum(1 for w in words if any(c.isdigit() for c in w))
    return (digit_words / len(words)) > NUMERIC_RUN_DIGIT_RATIO


@dataclass
class VerbatimGateRecord:
    claim_id: str
    section_id: str | None
    paragraph_id: int
    text: str
    handle: str | None
    run_words: int
    overlap_ratio: float
    matched_phrase: str
    status: str

    def to_dict(self) -> dict:
        return {
            "claim_id": self.claim_id,
            "section_id": self.section_id,
            "paragraph_id": self.paragraph_id,
            "text": self.text,
            "handle": self.handle,
            "run_words": self.run_words,
            "overlap_ratio": self.overlap_ratio,
            "matched_phrase": self.matched_phrase,
            "status": self.status,
        }


@dataclass
class VerbatimGateResult:
    total_factual_cited_claims: int = 0
    verbatim_risk_claims: int = 0
    numeric_legitimate_claims: int = 0
    records: list[VerbatimGateRecord] = field(default_factory=list)

    @property
    def verbatim_risk_claim_ids(self) -> list[str]:
        return [r.claim_id for r in self.records if r.status == VERBATIM_RISK]

    def to_dict(self) -> dict:
        return {
            "total_factual_cited_claims": self.total_factual_cited_claims,
            "verbatim_risk_claims": self.verbatim_risk_claims,
            "numeric_legitimate_claims": self.numeric_legitimate_claims,
            "verbatim_risk_claim_ids": self.verbatim_risk_claim_ids,
            "records": [r.to_dict() for r in self.records],
        }


def detect_verbatim_risk(
    pre_citation_markdown: str,
    post_citation_markdown: str,
    handle_to_evidence_text: Mapping[str, str],
    paragraph_section_ids: dict[int, str | None] | None = None,
) -> VerbatimGateResult:
    """Deterministic gate: for every cited factual/technical claim span,
    flag near-verbatim copying from its cited evidence text. Only records
    claims that HAVE a citation handle -- claims with none are the
    unsupported-claim gate's concern, not this one.
    """
    pre_blocks = pre_citation_markdown.split("\n\n")
    post_blocks = post_citation_markdown.split("\n\n")

    result = VerbatimGateResult()
    for para_idx, (pre_block, post_block) in enumerate(zip(pre_blocks, post_blocks)):
        if not is_substantive_prose(pre_block):
            continue
        spans = split_paragraph_into_spans(pre_block)
        span_handles = extract_span_citations(pre_block, post_block)
        section_id = paragraph_section_ids.get(para_idx) if paragraph_section_ids else None

        for span_index, ((_start, _end, text), handles) in enumerate(zip(spans, span_handles)):
            if classify_span_type(text) != FACTUAL_TECHNICAL or not handles:
                continue

            result.total_factual_cited_claims += 1
            claim_words = _tokenize(text)

            best_run = 0
            best_phrase: list[str] = []
            best_handle: str | None = None
            for h in handles:
                src_text = handle_to_evidence_text.get(h, "")
                if not src_text:
                    continue
                run, phrase = _longest_common_run(claim_words, _tokenize(src_text))
                if run > best_run:
                    best_run, best_phrase, best_handle = run, phrase, h

            if best_run >= MIN_RUN_WORDS:
                status = NUMERIC_LEGITIMATE if _is_numeric_run(best_phrase) else VERBATIM_RISK
            else:
                status = CLEAN

            if status == VERBATIM_RISK:
                result.verbatim_risk_claims += 1
            elif status == NUMERIC_LEGITIMATE:
                result.numeric_legitimate_claims += 1

            if status != CLEAN:
                result.records.append(VerbatimGateRecord(
                    claim_id=f"p{para_idx}_s{span_index}",
                    section_id=section_id,
                    paragraph_id=para_idx,
                    text=text.strip(),
                    handle=best_handle,
                    run_words=best_run,
                    overlap_ratio=round(best_run / max(len(claim_words), 1), 2),
                    matched_phrase=" ".join(best_phrase),
                    status=status,
                ))

    return result
