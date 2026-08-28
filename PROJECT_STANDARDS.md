# LitReview Agent — Quy chuẩn Kiến trúc & Phát triển (P-165)

> **Bắt buộc đọc trước khi code.** File này mô tả kiến trúc hệ thống hiện tại và các quy tắc bắt buộc khi đóng góp code. PR vi phạm các mục đánh dấu 🔒 (đặc biệt là thay đổi cấu trúc hệ thống) sẽ **không được merge** cho tới khi sửa lại đúng chuẩn hoặc được cả nhóm đồng ý thay đổi chuẩn này trước.
>
> Cập nhật lần cuối: 2026-08-27, sau một phiên vá lỗi lớn (xem mục "Lịch sử sự cố" cuối file).

---

## 1. Tổng quan dự án

**LitReview Agent** — trợ lý AI hỗ trợ Systematic Literature Review (SLR) cho nghiên cứu khoa học: định hình đề tài, sinh tiêu chí sàng lọc, tìm kiếm Google Scholar + đối chiếu Scopus, sàng lọc AI, workspace RAG chat trên PDF, tổng hợp báo cáo tự động, xuất Excel/BibTeX.

Deployed live tại `https://www.c3-app-165.io.vn/`.

### Stack
| Thành phần | Công nghệ |
|---|---|
| Frontend | React 19 + Vite, deploy trên **Vercel** |
| Backend | FastAPI (Python 3.11+), deploy trên **AWS EC2** (chạy `uvicorn` trực tiếp, không Docker) |
| Database | SQLite (`./data/app.db`) trên production hiện tại — xem mục 6 về rủi ro |
| Vector Store | ChromaDB (embedded, `./data/chroma`) |
| LLM chính | Google Gemini (`gemini-3.6-flash`), qua hệ thống router tập trung |
| LLM phụ / RAG chat | OpenAI (`gpt-4o-mini`) |
| Embedding | OpenAI (`text-embedding-3-small`), gọi trực tiếp `api.openai.com` |

### Repo & Deploy
- Repo chính (private): `github.com/AI20K-Build-Phase-Cohort-3/P-165`
- Repo mirror (public, Vercel đọc từ đây để build): `github.com/NamHaiIT2HUST/litreview-backend`
- **Mỗi lần push phải đẩy lên CẢ HAI remote** (đã cấu hình `git push origin main` tự đẩy cả 2 — kiểm tra `git remote -v` nếu máy bạn chưa có).
- Backend EC2 **không có CI/CD tự động** — sau khi push, phải tự SSH vào EC2, `git pull`, và restart tiến trình `uvicorn` thủ công (xem mục 7).
- `vercel.json` chứa **IP EC2 hardcode** trong phần `rewrites` — đây là điểm dễ vỡ nhất hệ thống: EC2 restart → đổi IP → toàn bộ frontend gãy cho tới khi có ai sửa lại `vercel.json` và push.

---

## 2. 🔒 Kiến trúc cố định — KHÔNG được thay đổi khi chưa thảo luận với cả nhóm

### 2.1. Mọi lệnh gọi LLM PHẢI đi qua router tập trung (`src/services/llm/`)

```python
from src.services.llm import ainvoke_with_failover, get_llm

result, outcome = await ainvoke_with_failover(
    "task_name",                                   # phải có trong capability.py TASK_REGISTRY
    lambda client: client.with_structured_output(MySchema),  # hoặc lambda client: client cho free-form
    [("human", prompt)],
    temperature=0.3,
)
```

**Lý do tồn tại quy tắc này**: trước đây có ít nhất **5 nơi khác nhau** (`screening_service.py`, `slr_swarm_routes.py`, `gap_finder.py`, `deps_provider.py`, `rag_service.py`) mỗi nơi tự viết lại một "cascade" thử Gemini → Groq → OpenAI riêng, với thứ tự đọc key khác nhau, danh sách model hardcode khác nhau (nhiều cái đã bị Google/nhà cung cấp gỡ bỏ từ lâu mà không ai biết). Hậu quả: sửa 1 chỗ không ảnh hưởng 7 chỗ còn lại, cùng 1 lỗi (key chết, model bị gỡ) tái diễn nhiều lần, và mất hàng giờ debug mỗi lần vì mỗi tính năng lỗi một kiểu khác nhau dù cùng nguyên nhân.

**Cấm tuyệt đối:**
- Tự `import ChatGoogleGenerativeAI` / `ChatOpenAI` / `ChatGroq` và tự dựng logic thử-lần-lượt-nhiều-provider ở bất kỳ file nghiệp vụ nào (`src/services/*`, `src/api/*`, `src/agents/*`).
- Đọc trực tiếp `os.getenv("GEMINI_API_KEY")` hay tương tự trong code nghiệp vụ để chọn key — việc chọn key/model/provider chỉ được làm trong `src/services/llm/`.

**Nếu task mới cần LLM**: thêm 1 dòng vào `TASK_REGISTRY` trong `src/services/llm/capability.py` khai báo `json_schema` và `min_context` cần thiết, rồi gọi `ainvoke_with_failover`. Chỉ vậy thôi.

### 2.2. 3 Agent trong tab Cấu hình dùng 3 key Gemini riêng biệt

`GEMINI_KEY_SCOPE_OPTIMIZER`, `GEMINI_KEY_CRITERIA_GENERATOR`, `GEMINI_KEY_PICO` — cơ chế này nằm trong `_TASK_DEDICATED_GEMINI_ENV` ở `src/services/llm/router.py`. Nếu thêm agent thứ 4, thêm 1 dòng mapping task → biến `.env` mới ở đúng chỗ này, không đọc key kiểu tùy biến trong file agent.

**3 key này phải là 3 giá trị Gemini API key THẬT SỰ khác nhau** (không phải 1 key dùng chung nhiều tên biến) — nếu không, quota bị dùng chung, sập 1 cái là sập cả 3.

### 2.3. Xác thực & phân quyền dữ liệu

- Mọi route đọc/ghi dữ liệu gắn với 1 user phải có `Depends(get_current_user)` (từ `src/api/deps.py`).
- Mọi truy vấn trả về danh sách theo project (papers, workspace chat, search history...) **bắt buộc lọc theo `project_id` và kiểm tra quyền sở hữu** (user hiện tại có đúng là chủ project không, trừ admin). Xem `_authorize_project_access` trong `src/api/project_routes.py` làm mẫu.
- **Không** có "fallback lấy toàn bộ dữ liệu trong DB khi thiếu tham số lọc". Từng có bug: `workspace/chat` khi không truyền `paper_ids` thì quét TOÀN BỘ bảng `papers` không lọc theo project → 1 user có thể vô tình chat "trúng" tài liệu của project/user khác. Bài học: fallback im lặng luôn thu hẹp phạm vi (trả rỗng/báo lỗi), không bao giờ mở rộng phạm vi.
- **Không** tạo phiên đăng nhập giả ("offline fallback", "demo session") ở frontend khi backend không phản hồi. Đăng nhập thất bại phải báo lỗi rõ ràng, không bao giờ tự tạo token giả.

### 2.4. Cấu hình backend URL — 1 nguồn duy nhất

`frontend/src/utils/apiConfig.js` là nơi DUY NHẤT quyết định frontend gọi backend ở đâu. Không hardcode URL backend ở bất kỳ component nào khác. Xem `docs/architecture/DEPLOY_BACKEND_ORIGIN.md` để hiểu toàn bộ luồng.

### 2.5. `.env` là nguồn cấu hình runtime duy nhất, không commit

- `.env` nằm trong `.gitignore` — **không bao giờ commit file này**, kể cả vô tình qua `git add -A`.
- **`.env` trên máy local và `.env` trên EC2 là 2 file độc lập, không tự đồng bộ.** Sửa 1 bên không ảnh hưởng bên kia — luôn phải SSH vào EC2 sửa riêng.
- ⚠️ **Cẩn thận khi mở file `.env` bằng editor có auto-save/nhiều tab**: nếu bạn mở tab `.env` từ lâu rồi ai đó (kể cả AI) sửa file trên đĩa, tab cũ của bạn vẫn giữ nội dung stale — lỡ tay Ctrl+S sẽ **ghi đè mất toàn bộ thay đổi mới**. Sự cố này đã xảy ra thật trong phiên vá lỗi vừa rồi. Luôn "Reload from disk" trước khi sửa nếu nghi ngờ.
- `.env.example` phải luôn phản ánh đúng giá trị *loại biến* (không phải giá trị bí mật) đang thực sự dùng — nếu đổi model/provider mặc định, cập nhật cả `.env.example`.

---

## 3. Model & Key hiện hành (tránh nhầm — đã từng nhầm nhiều lần)

| Biến `.env` | Dùng cho | Giá trị hiện tại |
|---|---|---|
| `GEMINI_KEY_SCOPE_OPTIMIZER` | Agent 1 — Nhận xét phạm vi đề tài | Key Gemini riêng |
| `GEMINI_KEY_CRITERIA_GENERATOR` | Agent 2 — Sinh tiêu chí sàng lọc | Key Gemini riêng |
| `GEMINI_KEY_PICO` | Agent 3 — PICO & từ khóa | Key Gemini riêng |
| `GEMINI_MODEL` | Model Gemini dùng chung | `gemini-3.6-flash` — **model bị Google đổi tên định kỳ, nếu thấy lỗi 404 NOT_FOUND thì kiểm tra thông báo lỗi của Google, nó luôn ghi rõ tên model thay thế** |
| `OPENAI_API_KEY` + `OPENAI_MODEL` | Router (`src/services/llm/`) cho tab **Cấu hình** (3 agent: `optimize_scope`, `generate_criteria`, `extract_pico`, và `find_gaps`) + tab **Tìm kiếm** (AI Screening — `screen_paper`) | Key OpenAI thật (`sk-proj-...`), model `gpt-4o-mini`, gọi thẳng `api.openai.com`. Pin ở code (`_TASK_PREFERRED_PROVIDER` trong `router.py`) vì Gemini free-tier chỉ 20 req/ngày/model — hết quota trong vài phút ở usage thật của app. Gemini vẫn là fallback tự động nếu key này rỗng/lỗi. |
| `OPENAI_EMBEDDING_API_KEY` | Embedding (`text-embedding-3-small`) | Key OpenAI thật riêng, **khác** `OPENAI_API_KEY` ở trên — gọi thẳng `api.openai.com`, **không qua OpenRouter/xkiro nữa** (2 key đó đã xác nhận chết) |
| `LLM_API_KEY` + `LLM_API_BASE` + `LLM_MODEL` + `LLM_TEMPERATURE` | File riêng `src/services/eda_llm_client.py` (`build_eda_llm()`), chỉ dùng bởi tab **Phân tích** (EDA, `workspace_analyze_data()` trong `routes.py`) — **không dùng chung** `OPENAI_API_KEY`, không import gì từ `synthesis_llm_service.py` | Key gateway xkiro (`sk-xt-...`), `LLM_API_BASE=https://api.xkiro.com/v1`, `LLM_MODEL=deepseek/deepseek-v3.2`. Cố ý tách thành file riêng (không phải chỉ tham số override) để sửa provider/model cho tab này không bao giờ động tới router tập trung, `OPENAI_API_KEY`, hay pipeline Tổng hợp tài liệu — đổi 1 tab không kéo theo đổi tab kia. |
| `SYNTHESIS_LLM_PROVIDER` + `SYNTHESIS_MODEL` | `synthesis_llm_service` dùng chung cho pipeline **Tổng hợp tài liệu** (multi-paper synthesis, `src/services/synthesis_service.py`) | Vẫn `gemini` / `gemini-3.6-flash` — **không đổi khi đổi tab Phân tích**, 2 cái tách biệt dù cùng file `synthesis_llm_service.py` |
| `LLM_PROVIDER` | Chat RAG (`rag_service.py`, tab Workspace → Chat với nguồn) | Vẫn `gemini` — đọc trước `SYNTHESIS_LLM_PROVIDER` nên đổi biến kia không ảnh hưởng chat |
| `AI_LOG_API_KEY` | Log usage AI cho hệ thống chấm điểm khóa học — **key này gắn với DANH TÍNH CÁ NHÂN**, không phải cấu hình chung của app | Phải là key của **người đang code**, không dùng chung — mỗi thành viên tự thay key này trên máy mình khi code, đừng commit/chia sẻ giá trị cụ thể trong file chung |
| `SECRET_KEY` (JWT) | Ký token đăng nhập | Đã từng bị lộ (giá trị cũ nằm trong git history) — **không bao giờ đặt lại giá trị cũ `SUPER_SECRET_KEY_...`**, đó là secret đã compromised |

**Quy tắc cho `AI_LOG_API_KEY`**: đây là key cá nhân, gắn điểm số với từng người. Khi kéo code về, **kiểm tra lại giá trị này trong `.env` của mình có đúng key CỦA MÌNH không** trước khi bắt đầu code — nếu dùng nhầm key người khác, công sức bị tính nhầm cho họ và server chấm điểm **không hoàn tác được** khi phát hiện muộn (dedup theo nội dung, không re-assign được).

**Bug đã vá cùng đợt đổi `screen_paper` sang OpenAI (2026-08-27)**: `ScreenResponse.reason` ở `src/models/screening_schemas.py` từng khai báo kiểu `dict` trần (không có schema con) — chạy được trên Gemini nhưng OpenAI structured-output strict mode **reject thẳng** (`'additionalProperties' is required to be supplied and to be false`), khiến AI Screening luôn rơi vào nhánh lỗi im lặng (`relevance_bucket: "insufficient_info"`, thông báo chung chung "hệ thống đang gặp tải cao") mà không hề gọi được Gemini dự phòng (lỗi 400 bị phân loại permanent, không retry sang provider khác). Đã sửa: `reason` giờ là model con `ScreenReason` (matches/mismatches/exclusion_notes kiểu `List[str]`), và `screening_routes.py` gọi `.model_dump()` trước khi ghi vào cột `JSON` của DB. Bài học: đổi provider ưu tiên cho 1 task cũ đang chạy ổn trên Gemini **luôn cần test lại bằng tay** — Gemini và OpenAI không cùng độ nghiêm ngặt về JSON schema.

---

## 4. Quy tắc bắt buộc khi thêm/sửa tính năng

1. **Không tự viết lại logic đã có** — trước khi thêm 1 cascade/fallback mới, tìm trong `src/services/llm/` xem đã có chưa.
2. **Mọi route mới chạm dữ liệu user** phải qua `get_current_user` + kiểm tra ownership. PR thiếu việc này sẽ bị reject.
3. **Không đổi cấu trúc bảng DB** (thêm/xóa cột `db_models.py`) mà không thông báo trước — SQLite hiện tại dùng `create_all()`, không có migration Alembic hoạt động ổn định; đổi schema tùy tiện dễ vỡ dữ liệu production.
4. **Chạy `pytest tests/ -q` trước khi tạo PR.** Baseline hiện tại: 3 lỗi đã biết từ trước (`test_agent_basic_flow`, 2 test `SecurityConfigurationError`), không tính là regression. Nếu PR làm phát sinh lỗi mới ngoài 3 cái này → phải sửa trước khi merge.
5. **Build thử frontend** (`npm run build` trong `frontend/`) trước khi PR — không được để lỗi build.
6. **Deploy xong phải tự test tay trên web thật** (`c3-app-165.io.vn`) ít nhất luồng chính liên quan tới thay đổi của mình — CI hiện không tự động deploy/test E2E.
7. **Không hardcode bất kỳ URL backend, API key, hay model name nào** ngoài các vị trí đã quy định ở mục 2.

---

## 5. Quy trình merge

1. Code xong → `pytest` xanh (trừ 3 lỗi baseline) → `npm run build` xanh.
2. Push lên `origin main` (tự đẩy cả 2 remote).
3. Nếu có sửa code Python: SSH EC2 → `git pull` → restart `uvicorn` (mục 7) → tự test tay trên web thật.
4. Nếu có sửa `.env`/cấu hình: áp dụng thủ công trên **cả 2 nơi** (máy local + EC2), không có cách đồng bộ tự động.
5. Nếu PR đụng tới mục 2 (kiến trúc cố định) → bắt buộc thảo luận với cả nhóm trước, ghi rõ lý do trong PR description, cập nhật luôn file `PROJECT_STANDARDS.md` này nếu chuẩn thay đổi.

---

## 6. Rủi ro đã biết, chưa xử lý (không phải bug mới — đừng báo lại, hãy đọc rồi ưu tiên xử lý nếu rảnh)

- **SQLite trên production**: không chịu được nhiều user ghi đồng thời tốt bằng Postgres, và **không có backup tự động** — mất EC2 là mất dữ liệu. Khuyến nghị chuyển sang PostgreSQL khi có thời gian; docker-compose.yml đã có sẵn service Postgres để dùng.
- **~50 route ở `src/api/routes.py`** (search, workspace ngoài phần đã sửa, export...) **vẫn chưa có `get_current_user`** — chưa audit hết toàn bộ file này.
- **`vercel.json` IP hardcode** — cần Elastic IP hoặc domain riêng cho EC2 để không phải sửa tay mỗi lần EC2 khởi động lại.
- **`dedup_key` UNIQUE constraint crash** trong `_persist_search` (routes.py) khi 2 kết quả tìm kiếm trùng DOI — chưa bắt lỗi, làm rollback cả session DB, ảnh hưởng dây chuyền tới các request sau trong cùng transaction.
- **Verification Panel (Xác minh PDF)** chỉ hoạt động cho tài liệu upload qua `/workspace/direct-upload-json` sau khi có bản vá "gắn file ngầm" — cần theo dõi thêm độ ổn định.
- **Không có Celery worker chạy thật trên EC2** dù `docker-compose.yml` định nghĩa service `worker` — các job dùng `.delay()` (không phải `BackgroundTasks`) sẽ treo vô thời hạn nếu code nào đó chuyển sang dùng Celery. Hiện tại synthesis dùng `BackgroundTasks` (chạy trong tiến trình `uvicorn`) nên vẫn ổn — đừng đổi sang Celery trừ khi triển khai luôn worker + Redis thật trên EC2.

---

## 7. Lệnh restart backend trên EC2 (dùng mỗi lần deploy code Python mới)

```bash
cd /home/ubuntu/P-165
git pull origin main
pkill -f "uvicorn src.main:app"
sleep 1
source .venv/bin/activate
nohup python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8000 > uvicorn.log 2>&1 &
disown
sleep 2 && curl -s http://localhost:8000/health
```

Xem log realtime: `tail -f /home/ubuntu/P-165/uvicorn.log`

---

## 8. Lịch sử sự cố đáng nhớ (để không lặp lại)

- Đăng nhập Google từng có fallback tự tạo user giả (`google_session_...`) khi backend lỗi — đã bị phát hiện và xoá 2 lần (có nghĩa là ai đó đã thêm lại sau khi bị xoá lần đầu — cẩn thận khi review PR liên quan tới auth).
- 5 nơi khác nhau tự cài lại logic gọi LLM, dùng model đã bị nhà cung cấp gỡ bỏ từ lâu mà không ai biết — nguồn gốc phần lớn bug "AI trả lời sai/không trả lời" trong 1 đêm vá lỗi.
- `SECRET_KEY` và 1 API key OpenRouter/Gemini từng bị lộ ra ngoài (chat log, git history) và bị nhà cung cấp tự động thu hồi gần như ngay lập tức — **không bao giờ dán API key thật vào nơi có thể bị log/lưu công khai**, kể cả khi nhờ AI hỗ trợ debug; sửa `.env` trực tiếp trên server thay vì dán key vào chat.
