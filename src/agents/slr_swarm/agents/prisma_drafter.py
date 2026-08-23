"""Agent 4 — PRISMA Matrix & Auto Review Drafter (§5.4 Master Plan).

Trích xuất bảng so sánh PRISMA rồi soạn bản thảo LaTeX + BibTeX.
Luật cứng: một ô PRISMA chỉ được lên bản thảo nếu neo được về `[Page X, Line Y]`.
Ô không neo được sẽ hiện `n/a` chứ không được LLM "đoán cho có".
"""

from __future__ import annotations

import asyncio
import re

from src.agents.slr_swarm.contracts import (
    GroundedSpan,
    PaperRecord,
    PrismaRow,
    ReviewDraft,
)
from src.agents.slr_swarm.grounding import locate_claim
from src.agents.slr_swarm.json_utils import parse_object
from src.agents.slr_swarm.ports import SwarmDeps

PRISMA_SCHEMA = {
    "type": "object",
    "properties": {
        "design": {"type": "string"},
        "sample_size": {"type": "string"},
        "method": {"type": "string"},
        "outcome": {"type": "string"},
        "limitation": {"type": "string"},
    },
    "required": ["design", "sample_size", "method", "outcome"],
}

_FIELDS = ("design", "sample_size", "method", "outcome", "limitation")

_PROMPT = """Trích xuất thông tin PRISMA từ bài báo dưới đây.
Chỉ dùng chữ có trong bài. Nếu bài không nói, để chuỗi rỗng "" — TUYỆT ĐỐI không suy đoán.

Tiêu đề: {title}
Abstract: {abstract}

Trả về DUY NHẤT JSON với khoá: design, sample_size, method, outcome, limitation.
"""

_LATEX_ESCAPES = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def escape_latex(text: str) -> str:
    return "".join(_LATEX_ESCAPES.get(char, char) for char in text)


def cite_key(paper: PaperRecord) -> str:
    """Khoá BibTeX ổn định, an toàn: chỉ chữ/số/dấu hai chấm."""
    base = re.sub(r"[^A-Za-z0-9]+", "", paper.paper_id) or "ref"
    year = paper.year or "nd"
    return f"{base}{year}"


async def _extract_row(deps: SwarmDeps, paper: PaperRecord) -> PrismaRow:
    llm = deps.router.pick("extraction")
    raw = await llm.complete(
        _PROMPT.format(title=paper.title, abstract=paper.abstract),
        schema=PRISMA_SCHEMA,
    )
    data = parse_object(raw)

    try:
        pages = await deps.corpus.pages(paper.paper_id)
    except Exception:  # noqa: BLE001
        pages = []

    values: dict[str, str] = {}
    evidence: list[GroundedSpan] = []
    for field in _FIELDS:
        value = str(data.get(field, "") or "").strip()
        if not value:
            values[field] = ""
            continue
        span = locate_claim(f"{value}", paper.paper_id, pages)
        if span is None:
            # Không chứng minh được -> không cho vào bảng.
            values[field] = ""
            continue
        values[field] = value
        evidence.append(span)

    return PrismaRow(paper_id=paper.paper_id, evidence=evidence, **values)


def render_bibtex(papers: list[PaperRecord]) -> str:
    entries = []
    for paper in papers:
        fields = [f"  title = {{{paper.title}}}"]
        if paper.year:
            fields.append(f"  year = {{{paper.year}}}")
        if paper.venue:
            fields.append(f"  journal = {{{paper.venue}}}")
        if paper.doi:
            fields.append(f"  doi = {{{paper.doi}}}")
        entries.append("@article{" + cite_key(paper) + ",\n" + ",\n".join(fields) + "\n}")
    return "\n\n".join(entries)


def render_latex(rows: list[PrismaRow], papers: dict[str, PaperRecord]) -> tuple[str, int, int]:
    """Sinh chương Literature Review. Trả về (latex, tổng claim, số claim có bằng chứng)."""
    total = 0
    grounded = 0
    body: list[str] = [
        "\\section{Tổng quan tài liệu}",
        "",
        "\\begin{table}[h]",
        "\\centering",
        "\\caption{Ma trận so sánh PRISMA}",
        "\\begin{tabular}{p{2.2cm}p{2.2cm}p{2cm}p{3cm}p{3cm}}",
        "\\hline",
        "Nghiên cứu & Thiết kế & Cỡ mẫu & Phương pháp & Kết quả \\\\",
        "\\hline",
    ]

    for row in rows:
        paper = papers.get(row.paper_id)
        if paper is None:
            continue
        cells = []
        for field in ("design", "sample_size", "method", "outcome"):
            value = getattr(row, field)
            total += 1
            if value:
                grounded += 1
                cells.append(escape_latex(value))
            else:
                cells.append("n/a")
        label = escape_latex(paper.title[:40] or row.paper_id)
        body.append(f"{label} \\cite{{{cite_key(paper)}}} & " + " & ".join(cells) + " \\\\")

    body += ["\\hline", "\\end{tabular}", "\\end{table}", ""]

    # Phần diễn giải: mỗi câu đều kèm \cite + toạ độ trang để frontend anchor được.
    for row in rows:
        paper = papers.get(row.paper_id)
        if paper is None or not row.evidence:
            continue
        anchor = row.evidence[0]
        summary = row.outcome or row.method or row.design
        if not summary:
            continue
        body.append(
            f"{escape_latex(summary)} \\cite{{{cite_key(paper)}}} "
            f"% anchor: page {anchor.page}, lines {anchor.line_start}-{anchor.line_end}"
        )

    return "\n".join(body), total, grounded


async def run_prisma_drafter(state: dict, deps: SwarmDeps) -> dict:
    included = set(state.get("included_ids", []))
    corpus: list[PaperRecord] = [p for p in state.get("corpus", []) if p.paper_id in included]
    if not corpus:
        return {"error": "Agent 4: không có bài nào qua sàng lọc để dựng bảng PRISMA."}

    rows = list(await asyncio.gather(*(_extract_row(deps, p) for p in corpus)))
    papers = {p.paper_id: p for p in corpus}

    latex, total, grounded = render_latex(rows, papers)
    draft = ReviewDraft(
        latex=latex,
        bibtex=render_bibtex(corpus),
        claim_count=total,
        grounded_claim_count=grounded,
    )

    return {
        "prisma_rows": rows,
        "draft": draft,
        "trace": [
            {
                "agent": "prisma_drafter",
                "rows": len(rows),
                "claims": total,
                "grounded_claims": grounded,
            }
        ],
    }
