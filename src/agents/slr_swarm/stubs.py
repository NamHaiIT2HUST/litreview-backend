"""Adapter in-memory tất định cho SLR Swarm.

Mục đích: chạy end-to-end toàn bộ graph mà không cần API key, không cần vLLM,
không ra internet — phục vụ test và demo offline. Adapter thật (SerpApi / OpenAlex /
Ollama) chỉ cần implement đúng Protocol trong `ports.py` là thay được.
"""

from __future__ import annotations

import json
import re

from src.agents.slr_swarm.contracts import PaperRecord
from src.agents.slr_swarm.ports import PageText


class ScriptedLLM:
    """LLM giả: chọn câu trả lời theo dấu hiệu trong prompt.

    Ghi lại toàn bộ prompt vào `self.prompts` để test khẳng định được agent đã hỏi gì.
    """

    def __init__(self, responses: dict[str, str] | None = None, default: str = "{}"):
        self.responses = responses or {}
        self.default = default
        self.prompts: list[str] = []

    async def complete(self, prompt: str, *, schema: dict | None = None) -> str:
        self.prompts.append(prompt)
        for marker, response in self.responses.items():
            if marker in prompt:
                return response
        return self.default


class DefaultScriptedLLM(ScriptedLLM):
    """Bộ trả lời mặc định đủ để cả 5 agent chạy thông."""

    def __init__(self, keep_all: bool = True):
        pico = json.dumps(
            {
                "population": "bệnh nhân tim mạch",
                "intervention": "mô hình học sâu trên tín hiệu ECG",
                "comparison": "phương pháp thống kê truyền thống",
                "outcome": "độ chính xác chẩn đoán",
                "mesh_terms": ["Electrocardiography", "Deep Learning"],
                "axis_x": ["CNN", "Transformer"],
                "axis_y": ["người lớn", "trẻ em"],
            },
            ensure_ascii=False,
        )
        verdict = json.dumps(
            {
                "decision": "keep" if keep_all else "reject",
                "reason": "Bài nghiên cứu đúng quần thể và can thiệp quan tâm.",
                "confidence": 0.82,
                "evidence_quotes": ["we evaluated 500 patients with ECG recordings"],
            },
            ensure_ascii=False,
        )
        prisma = json.dumps(
            {
                "design": "retrospective cohort study",
                "sample_size": "500 patients",
                "method": "convolutional neural network",
                "outcome": "accuracy of 0.94",
                "limitation": "single center data",
            },
            ensure_ascii=False,
        )
        plan = json.dumps(
            {
                "methods": ["Descriptive statistics", "ANOVA"],
                "rationale": "Có biến phân loại và biến số liên tục.",
                "code": "import pandas as pd\ndf = pd.read_csv('data.csv')\nprint(df.describe())",
                "interpretation": "Xem p-value < 0.05 để kết luận khác biệt có ý nghĩa.",
            },
            ensure_ascii=False,
        )
        super().__init__(
            responses={
                "khung PICO": pico,
                "reviewer": verdict,
                "TRỌNG TÀI": verdict,
                "Trích xuất thông tin PRISMA": prisma,
                "chuyên gia thống kê": plan,
            },
            default="{}",
        )


class InMemorySearch:
    def __init__(self, papers: list[PaperRecord], match_all: bool = False):
        self.papers = papers
        self.match_all = match_all
        self.queries: list[str] = []

    async def search(self, query: str, *, limit: int = 20) -> list[PaperRecord]:
        self.queries.append(query)
        if self.match_all:
            return self.papers[:limit]
        terms = [t.lower() for t in re.findall(r'"([^"]+)"', query)] or [query.lower()]
        hits = [
            p
            for p in self.papers
            if any(term in f"{p.title} {p.abstract}".lower() for term in terms)
        ]
        return hits[:limit]


class InMemoryCitations:
    """Đồ thị trích dẫn: `edges[paper_id] = (references, citations)`."""

    def __init__(
        self,
        papers: dict[str, PaperRecord],
        edges: dict[str, tuple[list[str], list[str]]] | None = None,
    ):
        self.papers = papers
        self.edges = edges or {}

    def _lookup(self, ids: list[str]) -> list[PaperRecord]:
        return [self.papers[i] for i in ids if i in self.papers]

    async def references(self, paper_id: str) -> list[PaperRecord]:
        return self._lookup(self.edges.get(paper_id, ([], []))[0])

    async def citations(self, paper_id: str) -> list[PaperRecord]:
        return self._lookup(self.edges.get(paper_id, ([], []))[1])


class InMemoryCorpus:
    """Full-text theo trang. `texts[paper_id] = [trang1, trang2, ...]`, mỗi trang là chuỗi nhiều dòng."""

    def __init__(self, texts: dict[str, list[str]]):
        self.texts = texts

    async def pages(self, paper_id: str) -> list[PageText]:
        raw_pages = self.texts.get(paper_id)
        if not raw_pages:
            return []
        return [
            PageText(page=index + 1, lines=[line for line in page.splitlines() if line.strip()])
            for index, page in enumerate(raw_pages)
        ]
