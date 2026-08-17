"""Grounded Verifier — §7.1 Master Plan (chống bịa nguồn).

Nguyên tắc: LLM chỉ được phép *đề xuất* khẳng định; việc xác nhận khẳng định đó có
thật trong tài liệu gốc hay không do code tất định làm, không do LLM tự chấm điểm
mình. Mỗi claim được neo về `[Page X, Line Y]` để frontend highlight đúng chỗ.
"""

from __future__ import annotations

import re

from src.agents.slr_swarm.contracts import GroundedSpan
from src.agents.slr_swarm.ports import PageText

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Từ quá phổ biến, khớp trúng chúng không chứng minh được gì.
_STOPWORDS = frozenset(
    """a an the of in on at to for from with without by and or not is are was were be been
    this that these those we our their its it as than then such using used use study studies
    result results show shows showed between among during""".split()
)


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS and len(t) > 1]


def _overlap_score(claim_tokens: list[str], window_tokens: list[str]) -> float:
    """Tỉ lệ token nội dung của claim xuất hiện trong cửa sổ văn bản, có thưởng cho cụm liền.

    Trả về [0, 1]. Không dùng Jaccard vì đoạn trích thường dài hơn claim rất nhiều.
    """
    if not claim_tokens:
        return 0.0
    window = set(window_tokens)
    hits = sum(1 for t in claim_tokens if t in window)
    coverage = hits / len(claim_tokens)

    # Thưởng khi có bigram khớp: giảm khả năng "trúng từ rời rạc" nhưng sai ngữ cảnh.
    claim_bigrams = set(zip(claim_tokens, claim_tokens[1:]))
    if claim_bigrams:
        window_bigrams = set(zip(window_tokens, window_tokens[1:]))
        bigram_coverage = len(claim_bigrams & window_bigrams) / len(claim_bigrams)
    else:
        bigram_coverage = coverage

    return round(0.7 * coverage + 0.3 * bigram_coverage, 4)


def locate_claim(
    claim: str,
    paper_id: str,
    pages: list[PageText],
    *,
    window: int = 3,
    min_score: float = 0.5,
) -> GroundedSpan | None:
    """Tìm đoạn (tối đa `window` dòng liên tiếp) khớp nhất với claim.

    Trả về None nếu không có đoạn nào đạt `min_score` — tức claim này *không grounded*
    và phải bị loại khỏi bản thảo, không được "làm tròn" thành đúng.
    """
    claim_tokens = tokenize(claim)
    if not claim_tokens:
        return None

    best: GroundedSpan | None = None
    for page in pages:
        for start in range(len(page.lines)):
            for size in range(1, window + 1):
                end = start + size
                if end > len(page.lines):
                    break
                chunk = " ".join(page.lines[start:end])
                score = _overlap_score(claim_tokens, tokenize(chunk))
                if score < min_score:
                    continue
                # Điểm bằng nhau thì chọn đoạn hẹp hơn — anchor càng gọn càng dễ đọc.
                if best is not None and (
                    score < best.score
                    or (score == best.score and size >= best.line_end - best.line_start + 1)
                ):
                    continue
                best = GroundedSpan(
                        paper_id=paper_id,
                        page=page.page,
                        line_start=start + 1,
                        line_end=end,
                        quote=chunk.strip(),
                        score=score,
                    )
    return best


def verify_claims(
    claims: list[str],
    paper_id: str,
    pages: list[PageText],
    *,
    min_score: float = 0.5,
) -> tuple[list[GroundedSpan], float]:
    """Xác minh loạt claim. Trả về (spans tìm được, grounding score của bài báo).

    Grounding score = tỉ lệ claim có bằng chứng thật, KHÔNG phải điểm trung bình
    độ khớp — một claim bịa hoàn toàn phải kéo điểm xuống, không được ẩn đi.
    """
    if not claims:
        return [], 0.0

    spans: list[GroundedSpan] = []
    for claim in claims:
        span = locate_claim(claim, paper_id, pages, min_score=min_score)
        if span is not None:
            spans.append(span)

    return spans, round(len(spans) / len(claims), 4)
