"""Lắp ráp `SwarmDeps` mặc định cho runtime.

Skeleton: dùng adapter in-memory để pipeline chạy được ngay từ lần clone đầu.
Bước tích hợp thật thay từng port một (search → citations → corpus → LLM local),
không phải viết lại graph.
"""

from __future__ import annotations

from src.agents.slr_swarm.contracts import PaperRecord
from src.agents.slr_swarm.ports import ModelRouter, SwarmDeps
from src.agents.slr_swarm.stubs import (
    DefaultScriptedLLM,
    InMemoryCitations,
    InMemoryCorpus,
    InMemorySearch,
)

_DEMO_PAPERS = [
    PaperRecord(
        paper_id="P1",
        title="Deep learning for ECG arrhythmia detection",
        abstract="We evaluated 500 patients with ECG recordings using a convolutional neural network.",
        year=2023,
        venue="IEEE TBME",
        doi="10.1000/demo1",
        pdf_available=True,
    ),
    PaperRecord(
        paper_id="P2",
        title="Transformer models on cardiac signals",
        abstract="A transformer architecture applied to cardiac signals of adult patients.",
        year=2024,
        venue="Nature Digital Medicine",
        doi="10.1000/demo2",
        pdf_available=True,
    ),
]

_DEMO_FULLTEXT = {
    "P1": [
        "Deep learning for ECG arrhythmia detection\n"
        "In this retrospective cohort study we evaluated 500 patients with ECG recordings.\n"
        "The convolutional neural network reached an accuracy of 0.94 on the held out set.\n"
        "A limitation is that this is single center data.",
    ],
    "P2": [
        "Transformer models on cardiac signals\n"
        "We evaluated 500 patients with ECG recordings in a retrospective cohort study.\n"
        "Our convolutional neural network baseline reached an accuracy of 0.94.\n"
        "The main limitation is single center data collection.",
    ],
}


def build_default_deps(**overrides) -> SwarmDeps:
    papers = {p.paper_id: p for p in _DEMO_PAPERS}
    deps = SwarmDeps(
        router=ModelRouter(local=DefaultScriptedLLM()),
        search=InMemorySearch(_DEMO_PAPERS, match_all=True),
        citations=InMemoryCitations(papers, edges={"P1": ([], ["P2"])}),
        corpus=InMemoryCorpus(_DEMO_FULLTEXT),
        min_papers=2,
        baseline_minutes=14 * 8 * 60,
    )
    for key, value in overrides.items():
        setattr(deps, key, value)
    return deps
