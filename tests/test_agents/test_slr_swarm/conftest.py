from __future__ import annotations

import pytest

from src.agents.slr_swarm.contracts import PaperRecord
from src.agents.slr_swarm.ports import ModelRouter, SwarmDeps
from src.agents.slr_swarm.stubs import (
    DefaultScriptedLLM,
    InMemoryCitations,
    InMemoryCorpus,
    InMemorySearch,
)

FULLTEXT = {
    "P1": [
        "Deep learning for ECG arrhythmia detection\n"
        "In this retrospective cohort study we evaluated 500 patients with ECG recordings.\n"
        "The convolutional neural network reached an accuracy of 0.94 on the test set.\n"
        "A limitation is that this is single center data.",
    ],
    "P2": [
        "Transformer models on cardiac signals\n"
        "We evaluated 500 patients with ECG recordings across two hospitals.\n"
        "The convolutional neural network reached an accuracy of 0.94.\n"
        "The main limitation is single center data collection.",
    ],
    "P3": [
        "Unrelated paper about soil chemistry\n"
        "We measured nitrogen levels in agricultural plots over three seasons.",
    ],
}


@pytest.fixture
def papers() -> list[PaperRecord]:
    return [
        PaperRecord(
            paper_id="P1",
            title="Deep learning for ECG arrhythmia detection",
            abstract="We evaluated 500 patients with ECG recordings using a convolutional neural network.",
            year=2023,
            venue="IEEE TBME",
            doi="10.1000/demo1",
        ),
        PaperRecord(
            paper_id="P2",
            title="Transformer models on cardiac signals",
            abstract="A transformer applied to cardiac signals of adult patients.",
            year=2024,
            venue="Nature Digital Medicine",
        ),
        PaperRecord(
            paper_id="P3",
            title="Soil chemistry in agricultural plots",
            abstract="Nitrogen levels measured across three seasons.",
            year=2019,
        ),
    ]


@pytest.fixture
def make_deps(papers):
    def _make(**overrides) -> SwarmDeps:
        by_id = {p.paper_id: p for p in papers}
        searchable = overrides.pop("search_papers", papers)
        deps = SwarmDeps(
            router=ModelRouter(local=overrides.pop("llm", None) or DefaultScriptedLLM()),
            search=InMemorySearch(searchable, match_all=overrides.pop("match_all", True)),
            citations=InMemoryCitations(by_id, edges={"P1": (["P3"], ["P2"])}),
            corpus=InMemoryCorpus(FULLTEXT),
            min_papers=2,
        )
        for key, value in overrides.items():
            setattr(deps, key, value)
        return deps

    return _make
