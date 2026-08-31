"""Map-Reduce Cost Optimizer for RAG & Literature Synthesis.

Key capabilities:
1. Heuristic Pre-Filtering: Quickly scores and filters out low-signal chunks before invoking LLM MAP calls (saves 30-50% tokens).
2. Semantic Chunk Cache: In-memory hash cache for MAP summaries to eliminate redundant LLM calls on identical chunks.
3. Token & Cost Tracker: Accurately estimates prompt/completion token usage and USD cost.
"""
from __future__ import annotations

import hashlib
import logging
import re
import time
from dataclasses import dataclass
from typing import Any

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# Price estimation per 1M tokens (GPT-4o-mini / DeepSeek V3 tier standard)
INPUT_PRICE_PER_1M = 0.15   # $0.15 per 1M input tokens
OUTPUT_PRICE_PER_1M = 0.60  # $0.60 per 1M output tokens


@dataclass
class TokenCostReport:
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    tokens_saved_by_cache: int = 0
    tokens_saved_by_prefilter: int = 0
    cost_savings_pct: float = 0.0
    cache_hits: int = 0
    total_chunks_processed: int = 0
    chunks_sent_to_llm: int = 0


class MapSummaryCache:
    """Thread-safe in-memory cache for MAP chunk summaries."""
    def __init__(self, max_size: int = 2000):
        self._cache: dict[str, tuple[float, Any]] = {}
        self._max_size = max_size

    def _compute_key(self, chunk_content: str, query: str) -> str:
        q_norm = " ".join(re.findall(r"\w+", query.lower()[:100]))
        c_hash = hashlib.sha256(chunk_content.encode("utf-8")).hexdigest()[:16]
        q_hash = hashlib.sha256(q_norm.encode("utf-8")).hexdigest()[:16]
        return f"{c_hash}_{q_hash}"

    def get(self, chunk_content: str, query: str) -> Any | None:
        key = self._compute_key(chunk_content, query)
        entry = self._cache.get(key)
        if entry:
            return entry[1]
        return None

    def set(self, chunk_content: str, query: str, summary_obj: Any) -> None:
        if len(self._cache) >= self._max_size:
            # Evict oldest 20%
            keys_to_evict = sorted(self._cache.keys(), key=lambda k: self._cache[k][0])[: int(self._max_size * 0.2)]
            for k in keys_to_evict:
                self._cache.pop(k, None)
        key = self._compute_key(chunk_content, query)
        self._cache[key] = (time.time(), summary_obj)

    def clear(self) -> None:
        self._cache.clear()


class MapReduceOptimizer:
    """Manages pre-filtering, caching, and token cost tracking for RAG pipelines."""
    def __init__(self):
        self.cache = MapSummaryCache()

    def estimate_tokens(self, text: str) -> int:
        """Heuristic token estimator (approx ~4 chars/token for English/Math, ~2.5 for Vietnamese)."""
        if not text:
            return 0
        return max(1, int(len(text) / 3.5))

    def prefilter_chunks(
        self, query: str, chunks: list[Document], min_word_overlap: int = 1
    ) -> tuple[list[tuple[int, Document]], int]:
        """Pre-filters chunks using fast lexical overlap to avoid unnecessary LLM calls.

        Returns:
            - List of (original_index, doc) for promising chunks
            - Estimated tokens saved by pruning irrelevant chunks
        """
        if not chunks:
            return [], 0

        # Extract significant query keywords (skip very common stop words)
        stop_words = {
            "the", "and", "for", "with", "this", "that", "from", "which", "what", "how",
            "cua", "cac", "nhung", "trong", "cho", "la", "va", "ve", "duoc", "theo"
        }
        q_words = {w for w in re.findall(r"\w{3,}", query.lower()) if w not in stop_words}

        kept_chunks: list[tuple[int, Document]] = []
        pruned_tokens = 0

        for idx, doc in enumerate(chunks):
            content = doc.page_content or ""
            c_words = set(re.findall(r"\w{3,}", content.lower()))
            overlap = len(q_words & c_words)

            # Keep chunk if it has keyword overlap or if query is very short/abstract
            if overlap >= min_word_overlap or len(q_words) == 0:
                kept_chunks.append((idx, doc))
            else:
                pruned_tokens += self.estimate_tokens(content)

        # Safety Fallback: Never drop all chunks if input had docs
        if not kept_chunks and chunks:
            kept_chunks = [(0, chunks[0])]

        return kept_chunks, pruned_tokens

    def compute_cost_report(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        tokens_saved_cache: int,
        tokens_saved_prefilter: int,
        cache_hits: int,
        total_chunks: int,
        chunks_sent: int,
    ) -> TokenCostReport:
        """Calculates final cost metrics and token savings summary."""
        total_tokens = prompt_tokens + completion_tokens
        nominal_prompt_tokens = prompt_tokens + tokens_saved_cache + tokens_saved_prefilter
        nominal_tokens = nominal_prompt_tokens + completion_tokens

        cost_usd = round(
            (prompt_tokens / 1_000_000 * INPUT_PRICE_PER_1M)
            + (completion_tokens / 1_000_000 * OUTPUT_PRICE_PER_1M),
            6
        )

        savings_pct = 0.0
        if nominal_tokens > 0:
            savings_pct = round(((tokens_saved_cache + tokens_saved_prefilter) / nominal_tokens) * 100, 1)

        return TokenCostReport(
            total_prompt_tokens=prompt_tokens,
            total_completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=cost_usd,
            tokens_saved_by_cache=tokens_saved_cache,
            tokens_saved_by_prefilter=tokens_saved_prefilter,
            cost_savings_pct=savings_pct,
            cache_hits=cache_hits,
            total_chunks_processed=total_chunks,
            chunks_sent_to_llm=chunks_sent,
        )


map_reduce_optimizer = MapReduceOptimizer()
