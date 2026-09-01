# 🤖 AI Logs — LLM Call Tracing

Tài liệu này mô tả cơ chế trace các lệnh gọi LLM trong AI agent pipeline (Research Setup, AI Screening, RAG Chat, Synthesis), chứng minh hệ thống hoạt động đúng và có thể trace được.

> ⚠️ **Lưu ý:** Dự án có tích hợp sẵn LangSmith (`LANGCHAIN_TRACING_V2`) trong code, nhưng gặp lỗi 403 khi test ở Week 2 (xem [JOURNAL.md](../JOURNAL.md)) nên hiện bị **tắt cứng** tại [`src/main.py:9-10`](../src/main.py) — chạy bất kỳ môi trường nào cũng không gửi trace lên LangSmith. Team dùng cơ chế trace tự viết bên dưới, lưu trực tiếp vào Postgres, không phụ thuộc dịch vụ ngoài.

---

## ⚙️ Cơ chế: DB-backed LLM Call Log

Mỗi lệnh gọi LLM trong pipeline Synthesis được bọc trong `llm_trace()` ([`src/services/synthesis_llm_service.py:40`](../src/services/synthesis_llm_service.py)) và ghi 1 dòng vào bảng `llm_call_logs` (model `LLMCallLog`, [`src/models/db_models.py:600`](../src/models/db_models.py)):

| Cột | Nội dung |
|-----|----------|
| `session_id` | Gắn với `synthesis_sessions.id` — trace theo từng phiên tổng hợp |
| `step_name` | Tên bước pipeline (xem bảng bên dưới) |
| `model_name`, `attempt` | Model LLM dùng, số lần retry |
| `prompt_json` / `response_json` | Prompt gửi đi và response trả về — đầy đủ, không tóm tắt |
| `duration_ms`, `status`, `error` | Thời gian chạy, trạng thái, lỗi nếu có |

### Các bước pipeline được trace

`extract_evidence` · `extract_paper_evidence_batch` (+ `_custom`) · `propose_claims` · `verify_claim_set_tier2_nli` · `verify_claim_set_batch` (+ `_retry`, `_fallback`) · `deduplicate_evidence` · `build_outline` · `draft_section` · `qa_review_attempt_N` · `refine_section_attempt_N`

Xem toàn bộ điểm gọi tại [`src/services/synthesis_service.py`](../src/services/synthesis_service.py).

---

## 📊 Tổng hợp: Synthesis Metrics → Admin Dashboard

Mỗi session tổng hợp về 1 dòng `synthesis_metrics` (`total_llm_calls`, `total_input_tokens`, `total_output_tokens`, `cache_hits`/`cache_misses`, `grounding_retry_count`...). Token usage được cộng dồn theo từng user và hiển thị **thật** trên Admin Dashboard qua API `GET /auth/admin/stats` ([`src/api/auth_routes.py:173`](../src/api/auth_routes.py)) — số liệu lấy trực tiếp từ DB, không phải giả lập.

**Cách lấy screenshot:**
1. Đăng nhập tài khoản admin tại [c3-app-165.io.vn](https://www.c3-app-165.io.vn/) → vào **Admin Dashboard**
2. Screenshot bảng token usage theo tài khoản (input/output tokens, số project, số query mỗi user)

<!-- TODO: Paste screenshot Admin Dashboard tại đây -->

---

## 🔍 Trace chi tiết (raw prompt/response từng lệnh gọi)

Chưa có UI riêng để xem `llm_call_logs`, nhưng có thể query trực tiếp Postgres để lấy trace của 1 session cụ thể:

```sql
SELECT step_name, model_name, attempt, duration_ms, status, created_at
FROM llm_call_logs
WHERE session_id = '<synthesis_session_id>'
ORDER BY created_at;
```

<!-- TODO: Paste screenshot kết quả query (psql / DB client) tại đây -->

---

## Làm rõ: LangSmith vs Braintrust (tránh nhầm lẫn)

- **LangSmith** — có sẵn trong `requirements.lock` và biến môi trường `LANGCHAIN_*`, nhưng bị tắt cứng trong code do lỗi 403 gặp phải lúc test. Không phải cơ chế trace đang dùng cho deliverable này.
- **Braintrust** — chỉ dùng để mirror `.ai-log/session.jsonl`, tức log **prompt thành viên team gõ cho AI coding assistant** (phục vụ chấm điểm sử dụng AI của AI20K). Đây là log về cách team code, **không phải** trace của AI agent bên trong sản phẩm. Xem [`scripts/upload_ailog_to_braintrust.py`](../scripts/upload_ailog_to_braintrust.py).
