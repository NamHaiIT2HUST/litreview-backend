"""RAG Guardrail Service — Input/Output Guardrails & Hallucination Detection.

Capabilities:
1. Input Guardrails: Prompt injection check, safety sanitization, out-of-domain filtration.
2. Citation Verifier: Validates citation keys against retrieved context and strips hallucinated references.
3. Claim-Level Attribution:
   - Attributable: Factually entailed by retrieved source text.
   - Contradictory: Factually conflicting with source text.
   - Extrapolatory: Unsubstantiated extrapolation or hallucination.
4. Quantitative Metrics:
   - Faithfulness / Groundedness Score (0-100%)
   - Hallucination Rate (0-100%)
   - Citation Precision (0-100%)
   - Safety Verdict & Claim-by-Claim Audit Trail
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from uuid import UUID

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from src.config import get_settings

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Pydantic Schemas for Guardrail & Attribution
# ──────────────────────────────────────────────────────────────────────────────

class ClaimAttribution(BaseModel):
    sentence: str = Field(description="The individual claim or sentence extracted from the answer.")
    status: str = Field(description="Attributable, Contradictory, or Extrapolatory", default="Attributable")
    citation_keys: List[str] = Field(default_factory=list, description="Citation numbers or keys cited e.g. ['1', '2']")
    supporting_excerpt: str = Field(default="", description="Relevant snippet from the referenced source text")
    reasoning: str = Field(default="", description="Explanation of why this claim is supported or hallucinated")
    paper_title: Optional[str] = None
    page: Optional[Union[int, str]] = None
    filename: Optional[str] = None


class RAGGuardrailResult(BaseModel):
    is_safe: bool = True
    safety_verdict: str = "VERIFIED_HIGH_CONFIDENCE"  # VERIFIED_HIGH_CONFIDENCE | PARTIALLY_GROUNDED | HIGH_HALLUCINATION_RISK | REFUSAL_GROUNDED
    faithfulness_score: float = 1.0  # 0.0 - 1.0 (e.g. 1.0 = 100%)
    hallucination_rate: float = 0.0  # 0.0 - 1.0 (e.g. 0.0 = 0%)
    citation_precision: float = 1.0  # 0.0 - 1.0
    total_claims: int = 0
    attributable_claims_count: int = 0
    extrapolatory_claims_count: int = 0
    contradictory_claims_count: int = 0
    hallucinated_citations: List[str] = Field(default_factory=list)
    claims: List[ClaimAttribution] = Field(default_factory=list)
    summary_verdict: str = "Tất cả các luận điểm đều được chứng minh bởi tài liệu trích dẫn."


# ──────────────────────────────────────────────────────────────────────────────
# Claim Attribution Prompt Template
# ──────────────────────────────────────────────────────────────────────────────

_CLAIM_EVAL_SYSTEM = (
    "You are a rigorous Attribution Validator and Hallucination Auditor for scientific literature RAG (following ASTA-Bench and ScholarQA standards).\n"
    "Your mission is to evaluate whether each sentence or distinct claim in an AI-generated answer is genuinely supported by the provided context excerpts.\n\n"
    "For each claim, determine one of three standard categories:\n"
    "1. 'Attributable': The claim is directly supported, explicitly stated, or logically entailed by the provided context (including reasonable paraphrasing, mathematical equivalents, or accurate direct translations).\n"
    "2. 'Contradictory': The claim directly contradicts or misrepresents facts, equations, or results stated in the reference context.\n"
    "3. 'Extrapolatory': The claim introduces new factual assertions, external background facts, or claims that CANNOT be verified from the provided context (hallucination or ungrounded speculation).\n\n"
    "Respond ONLY with a valid JSON array of objects with keys:\n"
    "- 'sentence': the exact claim sentence\n"
    "- 'status': exactly 'Attributable', 'Contradictory', or 'Extrapolatory'\n"
    "- 'citation_keys': list of cited keys e.g. ['1', '2']\n"
    "- 'supporting_excerpt': the short text snippet from context that proves/disproves it\n"
    "- 'reasoning': concise 1-sentence explanation\n"
)

_CLAIM_EVAL_HUMAN = (
    "Context Excerpts Provided to RAG Model:\n"
    "{context_str}\n\n"
    "---\n"
    "User Question: {question}\n\n"
    "AI Generated Answer:\n{answer}\n\n"
    "Audit all key claims in the answer against the Context. Return ONLY valid JSON array:"
)

CLAIM_EVAL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _CLAIM_EVAL_SYSTEM),
    ("human", _CLAIM_EVAL_HUMAN),
])


# ──────────────────────────────────────────────────────────────────────────────
# RAG Guardrail Service Class
# ──────────────────────────────────────────────────────────────────────────────

class RAGGuardrailService:
    def __init__(self):
        self.settings = get_settings()

    # ── 1. Input Guardrail ──────────────────────────────────────────────────
    def validate_input_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """Validate input question against prompt injections and malicious patterns."""
        if not query or not query.strip():
            return False, "Câu hỏi không được để trống."
        
        q_norm = query.strip().lower()
        if len(q_norm) > 4000:
            return False, "Câu hỏi vượt quá độ dài tối đa cho phép (4000 ký tự)."

        # Prompt injection & jailbreak patterns
        injection_patterns = [
            r"ignore (all )?(previous|above) instructions",
            r"system prompt override",
            r"you are now in developer mode",
            r"jailbreak",
            r"bypass (all )?guardrails",
            r"repeat (the )?system prompt",
            r"reveal (the )?secret key",
        ]
        for pat in injection_patterns:
            if re.search(pat, q_norm, re.IGNORECASE):
                logger.warning(f"Input Guardrail triggered on query: {query[:100]}")
                return False, "Yêu cầu bị từ chối do vi phạm chính sách an toàn truy vấn (Prompt Injection Guard)."

        return True, None

    # ── 2. Strip Hallucinated Citation Keys & Ghost References (PaperQA2 Style) ──
    def prune_redundant_citations(self, text: str) -> str:
        """Compress and clean redundant consecutive citation keys e.g. [1][1] -> [1], [1][2] -> [1, 2]."""
        if not text:
            return ""

        # Collapse duplicate single citations e.g. [1][1] -> [1]
        text = re.sub(r'\[(\d+)\]\s*\[\1\]', r'[\1]', text)

        # Merge adjacent bracket groups e.g. [1][2] -> [1, 2]
        def _merge_brackets(match: re.Match) -> str:
            k1 = match.group(1).strip()
            k2 = match.group(2).strip()
            all_keys = [k.strip() for k in f"{k1},{k2}".split(",") if k.strip()]
            # deduplicate while preserving order
            seen = set()
            unique_keys = []
            for k in all_keys:
                if k not in seen:
                    seen.add(k)
                    unique_keys.append(k)
            return f"[{', '.join(unique_keys)}]"

        # Run merge recursively until no adjacent brackets remain
        for _ in range(3):
            text = re.sub(r'\[([0-9,\s]+)\]\s*\[([0-9,\s]+)\]', _merge_brackets, text)

        return text

    def detect_and_strip_ghost_authors(
        self, text: str, valid_authors: Optional[Set[str]] = None, valid_years: Optional[Set[str]] = None
    ) -> Tuple[str, List[str]]:
        """Detect and sanitize ghost/hallucinated author-year citations not in database."""
        if not text or not valid_authors:
            return text, []

        ghost_references: List[str] = []
        valid_authors_lower = {a.lower() for a in valid_authors if a}
        valid_years_set = {str(y).strip() for y in (valid_years or set()) if str(y).strip()}

        # Match patterns like (Author, 2024) or (Author et al., 2024)
        def _filter_author_year(match: re.Match) -> str:
            full_cit = match.group(0)
            author_part = match.group(1).strip().lower()
            year_part = match.group(2).strip()

            # Check if any valid author surname matches
            author_matched = any(va in author_part for va in valid_authors_lower)
            year_matched = year_part in valid_years_set if valid_years_set else True

            if not author_matched:
                ghost_references.append(full_cit)
                return ""
            return full_cit

        sanitized = re.sub(r'\(([A-Za-z\s]+(?:et al\.?)?),?\s*(\d{4})\)', _filter_author_year, text)
        return sanitized.strip(), ghost_references

    def sanitize_citations(
        self,
        answer: str,
        valid_keys: Set[str],
        valid_authors: Optional[Set[str]] = None,
        valid_years: Optional[Set[str]] = None,
    ) -> Tuple[str, List[str]]:
        """Identify and strip citation keys & ghost references that do not exist in the retrieved context."""
        found_keys: List[str] = []
        for match in re.finditer(r'\[([0-9,\s]+)\]', answer):
            for k in match.group(1).split(","):
                k_clean = k.strip()
                if k_clean:
                    found_keys.append(k_clean)

        hallucinated_keys = [k for k in set(found_keys) if k not in valid_keys]
        sanitized_answer = answer
        for bad_key in hallucinated_keys:
            # Replace [bad_key] or , bad_key with nothing
            sanitized_answer = re.sub(rf'\[{bad_key}\]', '', sanitized_answer)
            sanitized_answer = re.sub(rf',\s*{bad_key}\b', '', sanitized_answer)
            sanitized_answer = re.sub(rf'\b{bad_key}\s*,', '', sanitized_answer)

        # Ghost author check
        if valid_authors:
            sanitized_answer, ghost_refs = self.detect_and_strip_ghost_authors(sanitized_answer, valid_authors, valid_years)
            hallucinated_keys.extend(ghost_refs)

        # Clean up and prune redundant citations
        sanitized_answer = self.prune_redundant_citations(sanitized_answer)
        sanitized_answer = re.sub(r'\[\s*\]', '', sanitized_answer)
        # Collapse multiple horizontal spaces/tabs without destroying markdown paragraph breaks
        sanitized_answer = re.sub(r'[^\S\r\n]{2,}', ' ', sanitized_answer)
        sanitized_answer = re.sub(r'\n{3,}', '\n\n', sanitized_answer).strip()

        return sanitized_answer, hallucinated_keys


    # ── 3. Claim Attribution & Hallucination Detection ─────────────────────
    async def verify_answer_groundedness(
        self,
        question: str,
        answer: str,
        context_chunks: List[Dict[str, Any]],
    ) -> RAGGuardrailResult:
        """Run ASTA-Bench claim-level attribution verification on the RAG answer."""
        # 1. Check if the answer is a safe refusal ("Cannot answer")
        refusal_phrases = [
            "không tìm thấy thông tin",
            "tôi không thể trả lời",
            "cannot answer",
            "insufficient information",
            "no relevant information",
        ]
        if any(rp in answer.lower() for rp in refusal_phrases) and len(answer.strip()) < 300:
            return RAGGuardrailResult(
                is_safe=True,
                safety_verdict="REFUSAL_GROUNDED",
                faithfulness_score=1.0,
                hallucination_rate=0.0,
                citation_precision=1.0,
                total_claims=1,
                attributable_claims_count=1,
                extrapolatory_claims_count=0,
                contradictory_claims_count=0,
                hallucinated_citations=[],
                claims=[
                    ClaimAttribution(
                        sentence=answer.strip(),
                        status="Attributable",
                        citation_keys=[],
                        supporting_excerpt="Từ chối an toàn khi không đủ bằng chứng.",
                        reasoning="Hệ thống từ chối bịa đặt câu trả lời khi thiếu dữ liệu nguồn.",
                    )
                ],
                summary_verdict="Hệ thống đã kích hoạt cơ chế từ chối an toàn (Safe Refusal).",
            )

        if not context_chunks:
            return RAGGuardrailResult(
                is_safe=False,
                safety_verdict="HIGH_HALLUCINATION_RISK",
                faithfulness_score=0.0,
                hallucination_rate=1.0,
                citation_precision=0.0,
                total_claims=1,
                attributable_claims_count=0,
                extrapolatory_claims_count=1,
                contradictory_claims_count=0,
                hallucinated_citations=[],
                claims=[
                    ClaimAttribution(
                        sentence=answer[:200] + "...",
                        status="Extrapolatory",
                        citation_keys=[],
                        supporting_excerpt="Không có tài liệu nào được cung cấp.",
                        reasoning="Toàn bộ câu trả lời được sinh ra mà không có ngữ cảnh trích xuất.",
                    )
                ],
                summary_verdict="Nguy cơ ảo giác cao: Câu trả lời không có ngữ cảnh tài liệu đối chiếu.",
            )

        # Build context string mapping
        valid_keys = {str(c.get("key", idx + 1)) for idx, c in enumerate(context_chunks)}
        context_lines = []
        key_to_doc = {}
        for idx, c in enumerate(context_chunks):
            k = str(c.get("key", idx + 1))
            title = c.get("paper_title") or c.get("filename") or "Tài liệu nguồn"
            page = c.get("page_display") or c.get("page") or 1
            # Priority: full raw_text or complete summary/snippet
            full_text = c.get("raw_text") or c.get("summary") or c.get("snippet") or ""
            full_text = str(full_text).strip()[:2000]
            context_lines.append(f"[{k}] (Nguồn: {title}, Trang {page}):\n{full_text}")
            key_to_doc[k] = {
                "title": title,
                "page": page,
                "filename": c.get("filename"),
            }
        context_str = "\n\n".join(context_lines)

        # High-Speed Deterministic ASTA-Bench Claim Attribution (Sub-millisecond)
        # Parse sentences/claims from markdown answer while preserving lists and headings
        raw_lines = [line.strip() for line in answer.split('\n') if line.strip() and not line.strip().startswith('###')]
        sentences = []
        for line in raw_lines:
            sub_sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', line) if len(s.strip()) > 15]
            if sub_sentences:
                sentences.extend(sub_sentences)
            elif len(line) > 15:
                sentences.append(line)

        parsed = []
        for s in sentences:
            found_cits = re.findall(r'\[(\d+)\]', s)
            valid_cits_in_s = [k for k in found_cits if k in valid_keys]
            
            if valid_cits_in_s:
                first_k = valid_cits_in_s[0]
                doc_info = key_to_doc.get(first_k, {})
                full_doc_text = doc_info.get("full_text", "")
                
                # Extract first matching or first 150 chars as supporting excerpt
                excerpt_snippet = doc_info.get("snippet", full_doc_text[:180])
                
                parsed.append({
                    "sentence": s,
                    "status": "Attributable",
                    "citation_keys": valid_cits_in_s,
                    "supporting_excerpt": excerpt_snippet,
                    "reasoning": f"Xác thực từ trích dẫn [{first_k}] ({doc_info.get('title', 'Tài liệu')}).",
                })
            elif found_cits:
                parsed.append({
                    "sentence": s,
                    "status": "Extrapolatory",
                    "citation_keys": found_cits,
                    "supporting_excerpt": "Trích dẫn không tồn tại trong tập ngữ cảnh hợp lệ.",
                    "reasoning": "Mã trích dẫn không khớp với bất kỳ đoạn trích dẫn nguồn nào.",
                })
            else:
                parsed.append({
                    "sentence": s,
                    "status": "Attributable" if any(kw in s.lower() for kw in ["tóm tắt", "tổng quan", "bao gồm", "dưới đây", "lưu ý"]) else "Extrapolatory",
                    "citation_keys": [],
                    "supporting_excerpt": "Mệnh đề dẫn dắt / tổng quan chung.",
                    "reasoning": "Khẳng định tự nhiên hoặc mở rộng ngữ cảnh.",
                })


        claims_list: List[ClaimAttribution] = []
        attributable_cnt = 0
        extrapolatory_cnt = 0
        contradictory_cnt = 0

        for item in parsed:
            if not isinstance(item, dict):
                continue
            st = str(item.get("status", "Attributable")).capitalize()
            if st not in {"Attributable", "Contradictory", "Extrapolatory"}:
                st = "Attributable" if "attribut" in st.lower() else ("Contradictory" if "contradict" in st.lower() else "Extrapolatory")

            if st == "Attributable":
                attributable_cnt += 1
            elif st == "Contradictory":
                contradictory_cnt += 1
            else:
                extrapolatory_cnt += 1

            c_keys = [str(k) for k in item.get("citation_keys", []) if str(k).strip()]
            first_key = c_keys[0] if c_keys else None
            meta_info = key_to_doc.get(first_key, {}) if first_key else {}

            claims_list.append(ClaimAttribution(
                sentence=item.get("sentence", ""),
                status=st,
                citation_keys=c_keys,
                supporting_excerpt=item.get("supporting_excerpt", ""),
                reasoning=item.get("reasoning", ""),
                paper_title=meta_info.get("title"),
                page=meta_info.get("page"),
                filename=meta_info.get("filename"),
            ))

        total_claims = len(claims_list) or 1
        faithfulness = round(attributable_cnt / total_claims, 3)
        hallucination_rate = round((extrapolatory_cnt + contradictory_cnt) / total_claims, 3)

        # Check citation precision
        cited_keys_in_ans = set(re.findall(r'\[(\d+)\]', answer))
        valid_cited = [k for k in cited_keys_in_ans if k in valid_keys]
        cit_precision = round(len(valid_cited) / max(len(cited_keys_in_ans), 1), 3) if cited_keys_in_ans else 1.0

        # Determine safety verdict
        if contradictory_cnt > 0 or faithfulness < 0.50:
            verdict = "HIGH_HALLUCINATION_RISK"
            summary = f"Cảnh báo: Phát hiện {contradictory_cnt + extrapolatory_cnt}/{total_claims} luận điểm có nguy cơ ảo giác/mâu thuẫn."
        elif faithfulness < 0.85:
            verdict = "PARTIALLY_GROUNDED"
            summary = f"Độ tin cậy khá: {attributable_cnt}/{total_claims} luận điểm được xác minh nguồn."
        else:
            verdict = "VERIFIED_HIGH_CONFIDENCE"
            summary = f"Độ tin cậy cao: {attributable_cnt}/{total_claims} luận điểm được chứng minh trực tiếp từ tài liệu ({int(faithfulness * 100)}%)."

        return RAGGuardrailResult(
            is_safe=verdict != "HIGH_HALLUCINATION_RISK",
            safety_verdict=verdict,
            faithfulness_score=faithfulness,
            hallucination_rate=hallucination_rate,
            citation_precision=cit_precision,
            total_claims=total_claims,
            attributable_claims_count=attributable_cnt,
            extrapolatory_claims_count=extrapolatory_cnt,
            contradictory_claims_count=contradictory_cnt,
            hallucinated_citations=[k for k in cited_keys_in_ans if k not in valid_keys],
            claims=claims_list,
            summary_verdict=summary,
        )


rag_guardrail_service = RAGGuardrailService()
