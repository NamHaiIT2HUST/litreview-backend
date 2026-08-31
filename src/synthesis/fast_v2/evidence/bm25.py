"""Lightweight in-process BM25 lexical scoring.

Not a persistent index -- scores a paper-scoped document set fetched fresh
per call. This is deliberately simple: P-165's corpus is a handful to a few
dozen SELECTED papers per review, not a full-corpus search engine, so
re-tokenizing and re-scoring a few hundred chunks in-process is fast and
avoids maintaining a second persistent index alongside Chroma.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence

_TOKEN_PATTERN = re.compile(r"\w+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_PATTERN.findall(text.lower())


def bm25_scores(
    query: str, documents: Sequence[str], *, k1: float = 1.5, b: float = 0.75
) -> list[float]:
    """Okapi BM25 score for ``query`` against each of ``documents``, in order."""
    if not documents:
        return []

    doc_tokens = [_tokenize(doc) for doc in documents]
    doc_lens = [len(tokens) for tokens in doc_tokens]
    avg_len = sum(doc_lens) / max(len(doc_lens), 1)
    n_docs = len(documents)

    df: Counter[str] = Counter()
    for tokens in doc_tokens:
        df.update(set(tokens))

    query_tokens = _tokenize(query)
    scores: list[float] = []
    for tokens, doc_len in zip(doc_tokens, doc_lens):
        term_freq = Counter(tokens)
        score = 0.0
        for term in query_tokens:
            doc_freq = df.get(term)
            if not doc_freq:
                continue
            idf = math.log((n_docs - doc_freq + 0.5) / (doc_freq + 0.5) + 1.0)
            tf = term_freq[term]
            denom = tf + k1 * (1.0 - b + b * (doc_len / max(avg_len, 1e-6)))
            score += idf * ((tf * (k1 + 1.0)) / max(denom, 1e-6))
        scores.append(score)
    return scores
