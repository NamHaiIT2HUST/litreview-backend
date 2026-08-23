"""Agent 3 — Dual-Agent Peer Screener & Grounded Verifier (§5.3 Master Plan).

Hai reviewer chạy song song trên cùng một bài với thiên hướng ngược nhau
(inclusive: sợ bỏ sót — strict: sợ nhận nhầm). Chỉ khi hai bên bất đồng mới gọi
reviewer thứ ba làm trọng tài, nên chi phí thêm chỉ phát sinh ở ca khó.

Điểm grounding KHÔNG do reviewer tự chấm: mọi trích dẫn reviewer đưa ra đều bị
`grounding.verify_claims` đối chiếu lại với full-text bài báo.
"""

from __future__ import annotations

import asyncio

from src.agents.slr_swarm.contracts import (
    Decision,
    PaperRecord,
    ReviewerOpinion,
    ScreeningVerdict,
)
from src.agents.slr_swarm.grounding import verify_claims
from src.agents.slr_swarm.json_utils import as_str_list, parse_object
from src.agents.slr_swarm.ports import SwarmDeps

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["keep", "reject", "unsure"]},
        "reason": {"type": "string"},
        "confidence": {"type": "number"},
        "evidence_quotes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["decision", "reason"],
}

_STANCES = {
    "inclusive": (
        "Bạn là reviewer THỨ NHẤT, ưu tiên KHÔNG BỎ SÓT bài liên quan. "
        "Chỉ loại khi bài rõ ràng lạc đề."
    ),
    "strict": (
        "Bạn là reviewer THỨ HAI, ưu tiên ĐỘ CHÍNH XÁC. "
        "Chỉ giữ khi bài thoả đầy đủ tiêu chí nhận vào."
    ),
    "adjudicator": (
        "Bạn là TRỌNG TÀI. Hai reviewer trước bất đồng. "
        "Ra quyết định cuối dựa trên tiêu chí, không chiều theo bên nào."
    ),
}

_PROMPT = """{stance}

Tiêu chí NHẬN VÀO:
{inclusion}

Tiêu chí LOẠI RA:
{exclusion}

Bài báo:
- Tiêu đề: {title}
- Abstract: {abstract}
{extra}
Trả về DUY NHẤT JSON: decision (keep|reject|unsure), reason, confidence (0-1),
evidence_quotes (list các câu TRÍCH NGUYÊN VĂN từ bài báo làm căn cứ — không được diễn giải lại).
"""


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) or "- (không nêu)"


def _normalize_decision(value: object) -> Decision:
    text = str(value or "").strip().lower()
    return text if text in ("keep", "reject", "unsure") else "unsure"  # type: ignore[return-value]


async def _ask(
    deps: SwarmDeps,
    stance: str,
    paper: PaperRecord,
    inclusion: list[str],
    exclusion: list[str],
    extra: str = "",
) -> tuple[ReviewerOpinion, list[str]]:
    llm = deps.router.pick("screening")
    prompt = _PROMPT.format(
        stance=_STANCES[stance],
        inclusion=_bullets(inclusion),
        exclusion=_bullets(exclusion),
        title=paper.title,
        abstract=paper.abstract,
        extra=extra,
    )
    raw = await llm.complete(prompt, schema=VERDICT_SCHEMA)
    data = parse_object(raw)

    try:
        confidence = float(data.get("confidence", 0.0) or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0

    opinion = ReviewerOpinion(
        reviewer=stance,
        decision=_normalize_decision(data.get("decision")),
        reason=str(data.get("reason", "") or ""),
        confidence=max(0.0, min(1.0, confidence)),
    )
    return opinion, as_str_list(data.get("evidence_quotes"))


async def screen_paper(
    deps: SwarmDeps,
    paper: PaperRecord,
    inclusion: list[str],
    exclusion: list[str],
) -> ScreeningVerdict:
    (opinion_a, quotes_a), (opinion_b, quotes_b) = await asyncio.gather(
        _ask(deps, "inclusive", paper, inclusion, exclusion),
        _ask(deps, "strict", paper, inclusion, exclusion),
    )

    opinions = [opinion_a, opinion_b]
    quotes = list(dict.fromkeys(quotes_a + quotes_b))
    disagreed = opinion_a.decision != opinion_b.decision

    if disagreed:
        extra = (
            f"\nÝ kiến reviewer 1 ({opinion_a.decision}): {opinion_a.reason}\n"
            f"Ý kiến reviewer 2 ({opinion_b.decision}): {opinion_b.reason}\n"
        )
        opinion_c, quotes_c = await _ask(deps, "adjudicator", paper, inclusion, exclusion, extra)
        opinions.append(opinion_c)
        quotes = list(dict.fromkeys(quotes + quotes_c))
        final = opinion_c
    else:
        final = opinion_a if opinion_a.confidence >= opinion_b.confidence else opinion_b

    # Verifier: mọi trích dẫn phải neo được về full-text, nếu không thì bị bỏ.
    try:
        pages = await deps.corpus.pages(paper.paper_id)
    except Exception:  # noqa: BLE001 - thiếu PDF thì coi như không có bằng chứng
        pages = []

    spans, grounding = verify_claims(quotes, paper.paper_id, pages)

    return ScreeningVerdict(
        paper_id=paper.paper_id,
        decision=final.decision,
        reason=final.reason,
        confidence=final.confidence,
        grounding_score=grounding,
        spans=spans,
        opinions=opinions,
        disagreed=disagreed,
    )


async def run_peer_screener(state: dict, deps: SwarmDeps) -> dict:
    corpus: list[PaperRecord] = state.get("corpus", [])
    if not corpus:
        return {"error": "Agent 3: corpus rỗng, không có gì để sàng lọc."}

    inclusion = state.get("inclusion_criteria", [])
    exclusion = state.get("exclusion_criteria", [])

    semaphore = asyncio.Semaphore(deps.extras.get("screening_concurrency", 8))

    async def guarded(paper: PaperRecord) -> ScreeningVerdict:
        async with semaphore:
            return await screen_paper(deps, paper, inclusion, exclusion)

    verdicts = list(await asyncio.gather(*(guarded(p) for p in corpus)))

    kept = [v for v in verdicts if v.decision == "keep"]
    # Precision tính trên các bài được GIỮ — đó là những bài sẽ đi vào bản thảo.
    precision = round(sum(v.grounding_score for v in kept) / len(kept), 4) if kept else 0.0

    warnings = list(state.get("warnings", []))
    if len(kept) < deps.min_papers:
        warnings.append(
            f"Cảnh báo: chỉ {len(kept)} bài qua sàng lọc (< {deps.min_papers}). "
            "Dữ liệu chưa đủ mạnh để đưa ra kết luận chắc chắn."
        )

    return {
        "verdicts": verdicts,
        "included_ids": [v.paper_id for v in kept],
        "grounding_precision": precision,
        "warnings": warnings,
        "trace": [
            {
                "agent": "peer_screener",
                "screened": len(verdicts),
                "kept": len(kept),
                "disagreements": sum(1 for v in verdicts if v.disagreed),
                "grounding_precision": precision,
            }
        ],
    }
