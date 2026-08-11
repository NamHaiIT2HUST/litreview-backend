"""
Integrity Guard — kiểm tra 1 DOI có bị rút (retracted) hay không, qua Crossref API.

Trạng thái trả về:
- "retracted": Crossref xác nhận có update-to loại retraction -> CHẶN, không cho vào Draft.
- "active": Crossref xác nhận tồn tại, không có retraction -> cho qua.
- "unknown": không tra được (thiếu DOI, Crossref lỗi/timeout, DOI không tồn tại)
             -> KHÔNG chặn (unknown != retracted, giữ nguyên nguyên tắc
             "không mặc định trạng thái không xác định thành xấu" như M1/S6).
"""
import httpx

CROSSREF_API = "https://api.crossref.org/works"
TIMEOUT_SECONDS = 8.0


async def check_retraction(doi: str) -> dict:
    """Tra 1 DOI qua Crossref, trả {status, detail}."""
    if not doi or not doi.strip():
        return {"status": "unknown", "detail": "Không có DOI để kiểm tra."}

    doi = doi.strip()
    url = f"{CROSSREF_API}/{doi}"

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            resp = await client.get(url, headers={"User-Agent": "LitReviewAgent/1.0 (mailto:contact@example.com)"})
    except httpx.RequestError as e:
        return {"status": "unknown", "detail": f"Không gọi được Crossref: {e}"}

    if resp.status_code == 404:
        return {"status": "unknown", "detail": "DOI không tồn tại trên Crossref."}
    if resp.status_code != 200:
        return {"status": "unknown", "detail": f"Crossref trả về status {resp.status_code}."}

    try:
        message = resp.json().get("message", {})
    except ValueError:
        return {"status": "unknown", "detail": "Không đọc được response JSON từ Crossref."}

    updates = message.get("update-to", [])
    for update in updates:
        if str(update.get("type", "")).lower() == "retraction":
            return {
                "status": "retracted",
                "detail": f"Bị rút, xem thông báo tại DOI {update.get('DOI', '')}",
            }

    return {"status": "active", "detail": "Không tìm thấy thông báo retraction trên Crossref."}
