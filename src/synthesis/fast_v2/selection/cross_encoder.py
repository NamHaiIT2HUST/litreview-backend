"""Real cross-encoder reranker adapter behind the frozen ``EvidenceReranker``
protocol.

Provenance -- which reranker this is, and why
---------------------------------------------
The validated Evidence-First / Evidence-Hygiene / Dimension-Aware v1 work ran
against the repository's **existing** cross-encoder reranker, not a bespoke
one. That reranker is:

``cross-encoder/ms-marco-MiniLM-L-6-v2``

declared at ``src/services/reranker.py:13`` on the
``feat/phase123-eval-hybrid-agentic`` worktree
(``.claude/worktrees/phase123-merge``), and imported verbatim by every
Evidence-First spike in that worktree:

* ``spike_evidence_first_v0.py:61``
* ``spike_evidence_first_v1_context_budget.py:61``
* ``spike_evidence_first_v2_section_routing.py:61``
* ``spike_global_extraction.py:45``
* ``spike_global_extraction_v2.py:31``

each as ``from src.services.reranker import rerank as cross_encoder_rerank``
and described in their own docstrings as "the existing cross-encoder
reranker" -- the same phrase the ADR uses.

``Qwen/Qwen3-Reranker-0.6B`` (``.claude/worktrees/scientific-reranker-mvp``,
``src/services/qwen_reranker.py:12``) is explicitly documented there as a
"Candidate replacement for the MiniLM reranker slot", never adopted, with real
inference deferred to Colab. It is therefore NOT what produced the v1 numbers,
and it is deliberately not implemented here.

The upstream call contract, reproduced exactly
-----------------------------------------------
Upstream (``src/services/reranker.py:23-32``)::

    pairs = [(query, doc.page_content) for doc in documents]
    scores = model.predict(pairs)
    ranked = sorted(zip(documents, scores), key=lambda i: i[1], reverse=True)
    return [(doc, float(score)) for doc, score in ranked[:top_k]]

Consequences this adapter preserves, unchanged:

* the **query comes first** in every pair;
* pairs are built in **input order**;
* scores are raw ``CrossEncoder.predict`` logits -- unbounded and legitimately
  **negative** (the hygiene spike recorded -0.49 and -1.47);
* the returned sequence is sorted **score-descending**, NOT input order.

The only shape change is the protocol's: this adapter returns ``(index,
score)`` pairs indexing back into the input ``texts`` rather than
``(Document, score)``. ``apply_reranker`` re-associates by that index, so no
positional zip can silently mis-pair evidence with scores.

Laziness
--------
``sentence_transformers`` is imported **inside** :meth:`load` only, mirroring
``src/synthesis/fast_v2/generator/openscholar.py``. Importing
``src.synthesis.fast_v2`` on a CPU-only machine must not pull in torch or
download a checkpoint.
"""
from __future__ import annotations

from typing import Any, Callable, Sequence

#: The exact checkpoint used by the validated experiments. Do not change it
#: without re-running the RQ1/RQ2 benchmark -- the recorded bank sizes and the
#: `score > 0` relevance gate are both tied to this model's score scale.
CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class CrossEncoderReranker:
    """``cross-encoder/ms-marco-MiniLM-L-6-v2`` behind ``EvidenceReranker``.

    Loads the checkpoint on first :meth:`rerank` call, never at import or
    construction time.
    """

    def __init__(
        self,
        *,
        model_name: str = CROSS_ENCODER_MODEL,
        top_k: int | None = None,
        model_factory: Callable[[str], Any] | None = None,
    ) -> None:
        self.model_name = model_name
        self.top_k = top_k
        self._model_factory = model_factory
        self._model: Any = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def _default_model_factory(self, model_name: str) -> Any:
        # Imported here, never at module scope -- see the module docstring.
        from sentence_transformers import CrossEncoder

        return CrossEncoder(model_name)

    def load(self) -> Any:
        """Materialise the cross-encoder. Downloads/loads the checkpoint."""
        if self._model is None:
            factory = self._model_factory or self._default_model_factory
            self._model = factory(self.model_name)
        return self._model

    def rerank(self, query: str, texts: Sequence[str]) -> list[tuple[int, float]]:
        """Score ``texts`` against ``query``; best first.

        Returns ``(index, score)`` where ``index`` refers into ``texts``.
        """
        candidates = list(texts)
        if not candidates:
            # Mirrors the upstream early return: an empty shortlist must never
            # be a reason to load a model.
            return []

        model = self.load()
        if model is None:
            raise RuntimeError(
                "Cross-encoder reranker unavailable. fast_v2 will not silently "
                "fall back to an unranked ordering -- inject IdentityReranker "
                "explicitly if you intend 'no reranking happened'."
            )

        pairs = [(query, text) for text in candidates]
        scores = model.predict(pairs)

        if len(scores) != len(candidates):
            raise ValueError(
                f"Cross-encoder returned {len(scores)} scores for "
                f"{len(candidates)} candidates; scores must be positional and "
                "complete, otherwise index re-association is unsound."
            )

        ranked = sorted(
            enumerate(float(score) for score in scores),
            key=lambda item: item[1],
            reverse=True,
        )
        if self.top_k is not None:
            ranked = ranked[: self.top_k]
        return ranked
