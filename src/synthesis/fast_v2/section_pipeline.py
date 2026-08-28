"""Section-scoped synthesis pipeline: Outline-First + Section Contexts + 1-Call Writer.

This module implements the simplified production synthesis architecture:
1. Accepts an approved/edited LongformOutlinePlan with stable section IDs.
2. For each section: retrieves per subquery, executes cross-query RRF fusion, caps to section shortlist.
3. Reranks section shortlist against composite section semantic objective (title + purpose).
4. Groups evidence by stable section ID (section_contexts[sec.id]).
5. Computes dynamic Writer max_output_tokens from total outline target words.
6. Executes ONE citation-free Initial Draft Writer call.
7. Runs the Batched Citation Agent (with strict prose-preservation invariant).
8. Deterministically binds citations to canonical PDF offsets.
"""
from __future__ import annotations

import asyncio
import json
import math
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Sequence
from uuid import UUID

from src.synthesis.fast_v2.citations.anthropic_citations import attribute_all_prose_paragraphs
from src.synthesis.fast_v2.citations.finalizer import FinalCitation
from src.synthesis.fast_v2.evidence.bank import GroundedEvidenceBank
from src.synthesis.fast_v2.evidence.models import EvidenceUnit
from src.synthesis.fast_v2.evidence.retrieval import EvidenceRetriever
from src.synthesis.fast_v2.hygiene.classifier import filter_evidence_units
from src.synthesis.fast_v2.pipeline import FastSynthesisV2Result
from src.synthesis.fast_v2.planning.research_lead import LongformOutlinePlan
from src.synthesis.fast_v2.selection.policy import EvidenceSelectionPolicy
from src.synthesis.fast_v2.selection.rerank import apply_reranker_many


class WriterIncompleteError(RuntimeError):
    """Raised when Writer LLM output is truncated (finish_reason='length' or ends_normally=False)."""
    pass

SECTION_WRITER_SYSTEM_PROMPT = """You are an expert scientific literature review writer.
Your mission is to write an exhaustive, rigorous, and deeply technical academic literature review based strictly on the provided research outline and section-specific evidence passages.

CRITICAL ARCHITECTURAL & GROUNDING RULES:
1. STRICT CITATION-FREE WRITING: Do NOT invent, guess, or insert ANY citation handles or bracketed markers (such as [1], [E001], [Xu2010]). You are the Writer; a dedicated downstream Citation Agent will attribute your prose. Write natural academic prose mentioning author names and years in narrative style when appropriate (e.g. 'Byrne (2002) introduced...', 'Gibali et al. (2020) demonstrated...').
2. FACTUAL FIDELITY & ZERO OVERCLAIM: Write ONLY facts, definitions, lemmas, convergence guarantees, and experimental findings directly supported by the evidence passages under each section. Do NOT speculate, extrapolate, or invent future roadmap claims not in the source text.
3. ADHERE TO THE APPROVED OUTLINE: Follow every section header and purpose exactly in the specified order. Satisfy the target word count per section with dense mathematical explanation, comparative analysis, and comprehensive coverage.
4. CROSS-PAPER SYNTHESIS: In each section, synthesize and compare the methods across the listed papers. Do NOT write isolated paper-by-paper summaries; contrast formulations, assumptions (convex vs non-convex), stepsize strategies, and convergence properties.
5. MATHEMATICAL RIGOR: Render all mathematical equations and set definitions clearly using LaTeX syntax ($...$ for inline and $$...$$ for display blocks).

Output ONLY the complete Markdown literature review starting directly with the document title (# Title). No preamble, commentary, or conversational filler."""


def format_section_contexts_prompt(
    outline: LongformOutlinePlan,
    section_contexts: dict[str, list[EvidenceUnit]],
) -> str:
    """Format the user prompt pairing each outline section with its specific evidence by stable section ID."""
    lines = [
        f"# RESEARCH TOPIC: {outline.research_question}",
        "",
        "## OUTLINE SPECIFICATION & SECTION EVIDENCE",
        "",
    ]
    for idx, sec in enumerate(outline.sections, 1):
        lines.append(f"### Section {idx}: {sec.title}")
        lines.append(f"- Section ID: {sec.id}")
        lines.append(f"- Purpose: {sec.purpose}")
        lines.append(f"- Target Words: {sec.target_words}")
        if sec.papers_to_compare:
            lines.append(f"- Key Papers to Compare: {', '.join(sec.papers_to_compare)}")
        lines.append("")
        lines.append(f"#### Evidence Passages for Section {idx} ({sec.title}):")
        units = section_contexts.get(sec.id, [])
        if not units:
            lines.append("*(Evidence Insufficient: State only strictly established general principles or declare specific empirical/technical details unobserved in the retrieved corpus. Do NOT fabricate ungrounded claims or borrow unverified context)*")
        else:
            for u in units:
                page_info = f" (Page {u.page + 1})" if u.page is not None else ""
                lines.append(f"[{u.evidence_id}] {u.title}{page_info}:")
                lines.append(f'"{u.text.strip()}"')
                lines.append("")
        lines.append("---")
        lines.append("")
    lines.append("Write the complete, in-depth literature review following the outline above.")
    return "\n".join(lines)


class SectionScopedSynthesisPipeline:
    """Production Outline-First & Section-Scoped Synthesis Pipeline."""

    def __init__(
        self,
        *,
        retriever: EvidenceRetriever,
        reranker: Any,
        writer_llm: Any,
        citation_llm: Any,
        selection_policy: EvidenceSelectionPolicy | None = None,
        candidates_per_dimension: int = 30,
        section_candidate_cap: int = 25,
        max_evidence_per_section: int = 8,
        writer_max_tokens: int = 8192,
        artifact_dir: str | None = None,
        citation_batch_size: int = 8,
        citation_concurrency: int = 4,
    ) -> None:
        self.retriever = retriever
        self.reranker = reranker
        self.writer_llm = writer_llm
        self.citation_llm = citation_llm
        self.selection_policy = selection_policy or EvidenceSelectionPolicy()
        self.candidates_per_dimension = candidates_per_dimension
        self.section_candidate_cap = section_candidate_cap
        self.max_evidence_per_section = max_evidence_per_section
        self.writer_max_tokens = writer_max_tokens
        self.artifact_dir = artifact_dir
        #: Deployment-latency-tuned defaults -- see
        #: docs/superpowers/plans/2026-08-27-citation-stage-latency-optimization.md
        #: for the benchmark that picked these. Configurable, not hardcoded,
        #: per that plan's explicit requirement.
        self.citation_batch_size = citation_batch_size
        self.citation_concurrency = citation_concurrency

    async def run(
        self,
        *,
        approved_outline: LongformOutlinePlan,
        paper_ids: Sequence[UUID],
    ) -> FastSynthesisV2Result:
        """Run end-to-end Section-Scoped Literature Review pipeline."""
        t0_total = time.perf_counter()
        timings: dict[str, float] = {}

        # ── 1. Section-Scoped Retrieval & Cross-Query RRF Fusion ──────────────
        t0_ret = time.perf_counter()
        section_raw_pools: dict[str, list[EvidenceUnit]] = {}
        section_rerank_queries: dict[str, str] = {}
        retrieval_diagnostics: list[dict[str, Any]] = []

        for sec in approved_outline.sections:
            queries = sec.retrieval_queries or (sec.title,)
            subquery_results: list[list[EvidenceUnit]] = []

            for q_text in queries:
                candidates = await self.retriever.retrieve(
                    q_text, limit=self.candidates_per_dimension
                )
                kept, _dropped = filter_evidence_units(candidates)
                subquery_results.append(kept)

            # Cross-query RRF fusion within the section
            rrf_scores: dict[str, float] = {}
            unit_by_id: dict[str, EvidenceUnit] = {}
            for rank_list in subquery_results:
                for rank, unit in enumerate(rank_list):
                    rrf_scores[unit.evidence_id] = rrf_scores.get(unit.evidence_id, 0.0) + 1.0 / (60 + rank + 1)
                    unit_by_id.setdefault(unit.evidence_id, unit)

            sorted_section_candidates = [
                unit_by_id[eid].with_scores(retrieval_score=rrf_scores[eid])
                for eid in sorted(rrf_scores, key=lambda eid: rrf_scores[eid], reverse=True)[:self.section_candidate_cap]
            ]

            section_raw_pools[sec.id] = sorted_section_candidates
            composite_query = f"{sec.title}. {sec.purpose}".strip() if sec.purpose else sec.title
            section_rerank_queries[sec.id] = composite_query

        timings["retrieval_ms"] = round((time.perf_counter() - t0_ret) * 1000.0, 3)

        # ── 2. Rerank Section Shortlists on CPU via GTE ModernBERT ────────────
        t0_rerank = time.perf_counter()
        rerank_requests: list[tuple[str, list[EvidenceUnit]]] = [
            (section_rerank_queries[sec.id], section_raw_pools[sec.id])
            for sec in approved_outline.sections
        ]

        reranked_groups = await asyncio.to_thread(
            apply_reranker_many,
            self.reranker,
            requests=rerank_requests,
        )
        timings["rerank_ms"] = round((time.perf_counter() - t0_rerank) * 1000.0, 3)

        section_contexts: dict[str, list[EvidenceUnit]] = {}
        selected_evidence_set: dict[str, EvidenceUnit] = {}

        for sec, scored_pool in zip(approved_outline.sections, reranked_groups):
            filtered = [
                u for u in scored_pool
                if (u.rerank_score if u.rerank_score is not None else -999.0) >= self.selection_policy.relevance_threshold
            ]
            section_selected = filtered[:self.max_evidence_per_section]
            section_contexts[sec.id] = section_selected
            for u in section_selected:
                selected_evidence_set[u.evidence_id] = u

            retrieval_diagnostics.append({
                "section_id": sec.id,
                "section_title": sec.title,
                "subqueries": sec.retrieval_queries,
                "fused_count": len(section_raw_pools.get(sec.id, [])),
                "selected_count": len(section_selected),
                "context_words": sum(len(u.text.split()) for u in section_selected),
                "top_score": section_selected[0].rerank_score if section_selected else None,
            })

        selected_evidence_list = list(selected_evidence_set.values())
        paper_distribution: dict[str, int] = {}
        pages_represented: dict[str, list[int]] = {}
        for unit in selected_evidence_list:
            paper_distribution[unit.title] = paper_distribution.get(unit.title, 0) + 1
            if unit.page is not None:
                p_list = pages_represented.setdefault(unit.title, [])
                if unit.page not in p_list:
                    p_list.append(unit.page)
        for p_list in pages_represented.values():
            p_list.sort()

        evidence_bank = GroundedEvidenceBank(
            question=approved_outline.research_question,
            dimensions=tuple(sec.title for sec in approved_outline.sections),
            evidence=tuple(selected_evidence_list),
            paper_distribution=paper_distribution,
            pages_represented=pages_represented,
            retrieval_ms=timings["retrieval_ms"],
            rerank_ms=timings["rerank_ms"],
        )

        # ── IMMEDIATE PERSISTENCE: full evidence pack + section->evidence
        # mapping, so a Citation-only benchmark/replay can reconstruct the
        # exact scoped-evidence inputs later without re-running retrieval/
        # rerank. Cheap (no LLM call), so this happens unconditionally.
        if self.artifact_dir:
            try:
                os.makedirs(self.artifact_dir, exist_ok=True)
                evidence_bank_payload = {
                    "selected_evidence": [
                        {
                            "evidence_id": u.evidence_id,
                            "paper_id": str(u.paper_id),
                            "title": u.title,
                            "page": u.page,
                            "text": u.text,
                            "rerank_score": u.rerank_score,
                        }
                        for u in selected_evidence_list
                    ],
                    "section_evidence_ids": {
                        sec_id: [u.evidence_id for u in units]
                        for sec_id, units in section_contexts.items()
                    },
                    "sections": [{"id": sec.id, "title": sec.title} for sec in approved_outline.sections],
                }
                with open(os.path.join(self.artifact_dir, "evidence_bank.json"), "w", encoding="utf-8") as f:
                    json.dump(evidence_bank_payload, f, indent=2, ensure_ascii=False)
            except Exception as pe:
                print(f"[Warning] Failed to persist evidence_bank.json: {pe}", flush=True)

        # ── 3. Dynamic Writer Budget & ONE Citation-Free Writer LLM Call ─────
        t0_writer = time.perf_counter()
        total_target_words = sum(sec.target_words for sec in approved_outline.sections)
        configured_max_output_tokens = self.writer_max_tokens or 8192
        derived_requested_tokens = math.ceil(total_target_words * 2.4)
        actual_max_tokens_sent = min(derived_requested_tokens, configured_max_output_tokens)

        user_prompt = format_section_contexts_prompt(
            outline=approved_outline,
            section_contexts=section_contexts,
        )

        messages = [
            {"role": "system", "content": SECTION_WRITER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        print(
            f"[Writer] Invoking Writer LLM (streaming) with requested_tokens={derived_requested_tokens}, "
            f"configured_max_tokens={configured_max_output_tokens}, actual_sent={actual_max_tokens_sent} "
            f"(target_words={total_target_words})...",
            flush=True,
        )

        chunks: list[str] = []
        last_chunk: Any = None
        writer_finish_reason: str | None = None
        usage_metadata: dict[str, Any] | None = None

        bound_writer = self.writer_llm.bind(max_tokens=actual_max_tokens_sent)
        try:
            async for chunk in bound_writer.astream(messages):
                chunks.append(chunk.content if hasattr(chunk, "content") else str(chunk))
                last_chunk = chunk
                r_meta = getattr(chunk, "response_metadata", {}) or {}
                if r_meta.get("finish_reason"):
                    writer_finish_reason = r_meta.get("finish_reason")
                if getattr(chunk, "usage_metadata", None):
                    usage_metadata = chunk.usage_metadata
            draft_markdown = "".join(chunks)
        except Exception as e:
            print(f"[Writer] bound_writer streaming failed with {e}, retrying with bound writer...", flush=True)
            chunks = []
            async for chunk in bound_writer.astream(messages):
                chunks.append(chunk.content if hasattr(chunk, "content") else str(chunk))
                last_chunk = chunk
                r_meta = getattr(chunk, "response_metadata", {}) or {}
                if r_meta.get("finish_reason"):
                    writer_finish_reason = r_meta.get("finish_reason")
                if getattr(chunk, "usage_metadata", None):
                    usage_metadata = chunk.usage_metadata
            draft_markdown = "".join(chunks)

        timings["generation_ms"] = round((time.perf_counter() - t0_writer) * 1000.0, 3)

        if writer_finish_reason is None and last_chunk is not None:
            writer_finish_reason = getattr(last_chunk, "response_metadata", {}).get("finish_reason")
        if writer_finish_reason is None:
            writer_finish_reason = "UNKNOWN"

        completion_tokens: Any = None
        if usage_metadata:
            completion_tokens = usage_metadata.get("output_tokens")
        if completion_tokens is None and last_chunk is not None:
            completion_tokens = getattr(last_chunk, "response_metadata", {}).get("token_usage", {}).get("completion_tokens")
        if completion_tokens is None:
            completion_tokens = "UNKNOWN"

        output_words = len(draft_markdown.split())
        ends_normally = bool(draft_markdown.rstrip().endswith((".", "!", "?", "```", "]", "$$")))

        writer_telemetry = {
            "approved_target_words": total_target_words,
            "derived_requested_tokens": derived_requested_tokens,
            "configured_max_output_tokens": configured_max_output_tokens,
            "actual_max_tokens_sent": actual_max_tokens_sent,
            "completion_tokens": completion_tokens,
            "finish_reason": writer_finish_reason,
            "words_generated": output_words,
            "ends_normally": ends_normally,
            "generation_latency_ms": timings["generation_ms"],
        }

        print(
            f"[Writer] Generated {output_words} words in {timings['generation_ms']/1000.0:.2f}s "
            f"(finish_reason={writer_finish_reason}, tokens={completion_tokens}).",
            flush=True,
        )

        # ── IMMEDIATE PERSISTENCE: Save clean Writer output and telemetry ────
        if self.artifact_dir:
            try:
                os.makedirs(self.artifact_dir, exist_ok=True)
                with open(os.path.join(self.artifact_dir, "writer_output_clean.md"), "w", encoding="utf-8") as f:
                    f.write(draft_markdown)
                with open(os.path.join(self.artifact_dir, "writer_telemetry.json"), "w", encoding="utf-8") as f:
                    json.dump(writer_telemetry, f, indent=2, ensure_ascii=False)
            except Exception as pe:
                print(f"[Warning] Failed to persist Writer intermediate artifacts: {pe}", flush=True)

        # ── WRITER COMPLETENESS GATE: Fail fast before Citation if truncated ─
        if writer_finish_reason == "length" or not ends_normally:
            err_msg = (
                f"Writer output incomplete: finish_reason='{writer_finish_reason}', "
                f"ends_normally={ends_normally}, words_generated={output_words}, "
                f"completion_tokens={completion_tokens}. Pipeline halting before Citation."
            )
            print(f"[Writer] ERROR: {err_msg}", flush=True)
            raise WriterIncompleteError(err_msg)

        # ── 4. Batched Citation Agent ─────────────────────────────────────────
        t0_cit = time.perf_counter()
        print(f"[Citation Agent] Attributing prose against {len(selected_evidence_list)} evidence units...", flush=True)
        attribution_result = await attribute_all_prose_paragraphs(
            llm=self.citation_llm,
            draft_markdown=draft_markdown,
            evidence=selected_evidence_list,
            batch_size=self.citation_batch_size,
            concurrency=self.citation_concurrency,
            section_evidence=section_contexts,
            sections=tuple((sec.id, sec.title) for sec in approved_outline.sections),
        )
        cited_text = attribution_result.attributed_markdown
        timings["citation_ms"] = round((time.perf_counter() - t0_cit) * 1000.0, 3)
        print(f"[Citation Agent] Attribution completed in {timings['citation_ms']/1000.0:.2f}s.", flush=True)

        # ── 5. Deterministic Provenance Binding ──────────────────────────────
        t0_prov = time.perf_counter()
        citations: list[FinalCitation] = []

        handle_to_unit: dict[str, EvidenceUnit] = {}
        for idx, u in enumerate(selected_evidence_list, 1):
            h_key = f"E{idx:03d}"
            handle_to_unit[h_key] = u

        for match in re.finditer(r"\[(E\d{3}(?:,\s*E\d{3})*)\]", cited_text):
            handles_raw = match.group(1).split(",")
            for h_str in handles_raw:
                h = h_str.strip()
                unit = handle_to_unit.get(h)
                if unit is None:
                    continue
                citations.append(
                    FinalCitation(
                        evidence_id=unit.evidence_id,
                        paper_id=unit.paper_id,
                        paper_title=unit.title,
                        citation_marker=f"[{h}]",
                        review_char_start=match.start(),
                        review_char_end=match.end(),
                        source_page=unit.page,
                        source_char_start=unit.page_char_start,
                        source_char_end=unit.page_char_end,
                        quoted_snippet=unit.text[:300] if unit.text else "",
                    )
                )

        attribution_result.telemetry.final_bound_citations = len(citations)
        timings["finalize_ms"] = round((time.perf_counter() - t0_prov) * 1000.0, 3)
        timings["total_ms"] = round((time.perf_counter() - t0_total) * 1000.0, 3)

        # ── IMMEDIATE PERSISTENCE: Save Citation & Provenance artifacts ─────
        if self.artifact_dir:
            try:
                os.makedirs(self.artifact_dir, exist_ok=True)
                with open(os.path.join(self.artifact_dir, "final_review_after_citations.md"), "w", encoding="utf-8") as f:
                    f.write(cited_text)
                with open(os.path.join(self.artifact_dir, "citation_telemetry.json"), "w", encoding="utf-8") as f:
                    json.dump(attribution_result.telemetry.to_dict(), f, indent=2, ensure_ascii=False)
                with open(os.path.join(self.artifact_dir, "bound_citations.json"), "w", encoding="utf-8") as f:
                    json.dump(
                        [vars(c) for c in citations],
                        f,
                        indent=2,
                        ensure_ascii=False,
                        default=str,
                    )
            except Exception as pe:
                print(f"[Warning] Failed to persist Citation intermediate artifacts: {pe}", flush=True)

        # Honest grounding signal, not a fixed "success" literal: this path
        # runs no semantic-entailment verification (see
        # grounding/interface.py::ClaimGroundingStatus -- "Deliberately has
        # no 'validated' member, nothing can claim that yet"), so
        # claim_grounding_status stays "unvalidated" regardless of citation
        # outcome. semantic_grounded/grounding_warning reflect what this
        # stage *did* check: whether any claim actually bound to real
        # evidence and the prose-diff invariant held. Previously hardcoded
        # to "grounded"/True unconditionally -- caught via a live
        # /synthesis/execute call that returned 0 final_bound_citations (all
        # 6 citation handles invalid_handles_rejected) yet still reported
        # grounded: true to the API consumer.
        citations_bound = bool(citations)
        prose_invariant_ok = attribution_result.overall_diff_passed
        if citations_bound and prose_invariant_ok:
            grounding_warning = ""
        elif not citations_bound:
            grounding_warning = (
                "No claims in this section could be bound to validated evidence "
                "(0 citations passed attribution)."
            )
        else:
            grounding_warning = "Prose-diff invariant failed after citation attribution."
        return FastSynthesisV2Result(
            text=cited_text,
            evidence_bank=evidence_bank,
            citations=tuple(citations),
            timings=timings,
            synthesis_mode="fast_v2_section_scoped",
            claim_grounding_status="unvalidated",
            grounding_warning=grounding_warning,
            citation_authority="p165_deterministic_finalizer",
            semantic_grounded=citations_bound and prose_invariant_ok,
            diagnostics={
                "approved_outline": approved_outline.to_dict(),
                "section_count": len(approved_outline.sections),
                "total_target_words": total_target_words,
                "output_words": output_words,
                "writer_telemetry": writer_telemetry,
                "total_gte_pairs": sum(len(pool) for pool in section_raw_pools.values()),
                "total_evidence_units_selected": len(selected_evidence_list),
                "retrieval_diagnostics": retrieval_diagnostics,
                "section_contexts_count": {s_id: len(units) for s_id, units in section_contexts.items()},
                "citation_coverage_telemetry": attribution_result.telemetry.to_dict(),
                "prose_invariant_passed": attribution_result.overall_diff_passed,
            },
        )
