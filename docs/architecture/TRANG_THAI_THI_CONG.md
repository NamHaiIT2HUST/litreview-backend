# Trạng thái thi công — Giai đoạn 0–5

Nhánh: `docs/system-contracts-audit-and-plan`. Cập nhật 2026-08-26.

Kế hoạch đầy đủ ở [SYSTEM_CONTRACTS.md](./SYSTEM_CONTRACTS.md). Tài liệu này chỉ ghi
**đã làm gì, chưa làm gì, và vì sao** — để tech lead review không phải đọc lại toàn bộ diff.

---

## Tóm tắt

| Giai đoạn | Trạng thái |
|---|---|
| 0 — Bảo mật | Xong |
| 1 — Chặn đốt tiền | Xong |
| 2 — Chuẩn hóa môi trường | Xong, trừ việc hợp nhất Alembic (xem "Cố ý hoãn") |
| 3 — Vector Index contract | Xong |
| 4 — LLM Router | Xong (đã chuyển 3 call site sang router) |
| 5 — API contract & dọn nợ | Xong phần toàn vẹn dữ liệu; contract test còn lại |
| 6 — Synthesis | Chưa bắt đầu (tạm gác theo yêu cầu) |

**Test:** 9 failed / 602 passed → **1 failed / 668 passed**. Lỗi còn lại
(`test_agent_basic_flow`) đã có từ trước nhánh này, không liên quan các thay đổi ở đây.

**Frontend:** `npm run build` chạy được, đã kiểm tra tại chỗ.

---

## BẮT BUỘC làm trước khi chạy

Nhánh này **cố ý** làm hỏng các cấu hình đang sai. Không làm những bước sau thì app
sẽ không khởi động — đó là chủ đích, thay cho việc chạy tiếp trong trạng thái sai.

**1. Thêm `SECRET_KEY` vào `.env`.** App từ chối khởi động nếu thiếu.

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

**2. Lấy lại `.env` từ `.env.example` mới.** File cũ bật `SYNTHESIS_MODE=fast_v2_experimental`
và `FAST_V2_RERANKER=cross_encoder`, trái với default an toàn trong `config.py`. Nếu anh
giữ `.env` cũ thì vẫn đang chạy pipeline thử nghiệm.

**3. Chọn database tường minh.** Không còn tự rơi về SQLite nữa. Hoặc chạy
`docker compose up -d db` (theo `DATABASE_URL` mặc định), hoặc đặt thẳng
`DATABASE_URL=sqlite:///./data/app.db`.

**4. Cài lại dependency từ lockfile.**

```bash
pip install -r requirements.lock
```

**5. Tạo `frontend/.env.local`** từ `frontend/.env.example`.

**6. Đăng nhập lại.** Token cũ trong localStorage được ký bằng `SECRET_KEY` hardcode cũ,
giờ không còn hợp lệ. Tài khoản `admin123/123` không còn được tạo tự động — tạo tài khoản
qua màn hình đăng ký, hoặc bật seed cho môi trường dev:

```env
APP_ENV=development
SEED_DEFAULT_ADMIN=true
SEED_ADMIN_USERNAME=admin
SEED_ADMIN_PASSWORD=<mật khẩu tự đặt>
```

---

## Giai đoạn 0 — Bảo mật

Commit `3f9bc57`.

| Việc | Nơi |
|---|---|
| Thêm `get_current_user` / `get_optional_user` / `require_admin` | `src/api/deps.py` (file mới) |
| Bảo vệ `/auth/admin/stats` và `/auth/admin/users/{id}` | `auth_routes.py` |
| `/projects` chỉ trả project của người gọi đã xác thực; bỏ tin `X-User-Id` | `project_routes.py` |
| `POST /auth/google` yêu cầu token Google chấp nhận, kiểm `aud`, trả 401 nếu không; phát access token thật | `auth_routes.py` |
| Bỏ `SECRET_KEY` hardcode | `auth_routes.py` |
| Seed admin thành opt-in, chỉ development, mật khẩu từ config | `main.py`, `config.py` |
| `validate_security_settings()` chặn khởi động khi cấu hình thiếu an toàn | `config.py` |
| `/health` không còn lộ prefix API key | `main.py` |
| CORS dùng `cors_origins` thật | `main.py` |
| Frontend: bỏ 3 đường đăng nhập giả, bắt buộc token thật, tự gắn token vào mọi request | `AuthContext.jsx`, `apiConfig.js`, `AuthModal.jsx` |

**Phát hiện thêm trong lúc làm** (chưa có trong audit gốc): `AuthContext.jsx` có nhánh
"Seamless Academic Session Creation" đăng nhập **bất kỳ ai gõ bất kỳ định danh nào,
không kiểm mật khẩu**, và lưu chuỗi `'local_session_token'` làm access token. Đã xóa.

### Chưa làm ở giai đoạn 0

56 route thì mới bảo vệ nhóm `/projects` và `/auth/admin/*`. Các route còn lại
(papers, search, synthesis, export, workspace, screening, slr-swarm) **vẫn chưa có
dependency xác thực**. Lý do: gắn `get_current_user` cho toàn bộ 56 route cùng lúc
sẽ làm hỏng những luồng đang dựa vào "Default Project" không có chủ, và không kiểm
chứng được trong một lần. Hạ tầng đã sẵn sàng — thêm
`Depends(get_current_user)` là đủ — nhưng cần làm theo từng nhóm route kèm thử UI.
**Đây là việc còn hở, cần ưu tiên tiếp theo.**

---

## Giai đoạn 1 — Chặn đốt tiền

Commit `3f9bc57`.

| Việc | Nơi |
|---|---|
| Bỏ fallback Gemini rồi `FakeEmbeddings` khi thiếu OpenAI key | `vector_store.py` |
| `add_documents` / `stage_documents_for_paper` raise thay vì trả `0` / `[]` | `vector_store.py` |
| Vector store singleton khởi tạo lười, để lỗi cấu hình không thành lỗi import | `vector_store.py` |
| Tách lỗi permanent (400/401/403/404/422) khỏi transient; permanent thì dừng ngay | `synthesis_llm_service.py` |
| Bỏ 2 candidate hardcode `gpt-4o-mini` / `gemini-2.0-flash` | `synthesis_llm_service.py` |
| Bỏ `sk-placeholder` và `claude-opus-5-thinking`, raise thay thế | `synthesis_llm_service.py` |
| `effective_gemini_api_key` xác định, bỏ `random.choice` | `config.py` |

**Tác động tính được:** một key sai trước đây chạy hết ma trận 6 candidate × 4 attempt
= tối đa 24 lệnh gọi tính phí cho một bước, tất cả đều fail. Giờ dừng ở lệnh gọi đầu tiên.

**Bằng chứng bản vá cũ từng bị đè:** test `test_openai_provider_raises_without_key`
(từ commit `5fbc555`, 23/8) **đang fail trên `main`** vì commit `a07f35a` đảo ngược hành vi
nhưng test vẫn còn. Thay đổi ở đây làm test đó xanh trở lại.

---

## Giai đoạn 2 — Chuẩn hóa môi trường

Commit `83fbde7`.

| Việc | Nơi |
|---|---|
| `requirements.lock`, 188 package pin, compile trên Python 3.11 khớp CI + Dockerfile | file mới |
| `npm ci` thay `npm install` ở cả 2 lệnh build | `package.json`, `vercel.json` |
| Bỏ fallback Postgres → SQLite, raise `DatabaseUnavailableError` | `database.py` |
| `DATABASE_URL` không còn bị mutate runtime (sửa luôn vụ import cũ ở `graph.py`, `synthesis_tasks.py`) | `database.py` |
| `safe_exec` log lỗi ALTER thay vì nuốt | `database.py` |
| Thư mục `data/` tạo theo project root, không theo CWD | `database.py` |
| Viết lại `.env.example` khớp default an toàn, bổ sung biến còn thiếu | `.env.example` |
| Tạo `frontend/.env.example` | file mới |
| Bỏ IP hardcode khỏi `apiConfig.js`; bỏ fallback mixed-content không bao giờ chạy được | `apiConfig.js` |
| CI tách 2 job, cài từ lockfile, build + lint frontend | `ci.yml` |

### Phát hiện mới quan trọng: rò rỉ `.env` giữa các worktree

`load_dotenv()` không tham số **tìm ngược lên thư mục cha**. Worktree ở
`.claude/worktrees/<tên>` đang âm thầm nạp `.env` của checkout chính — nghĩa là chạy
bằng provider, database và feature flag của người khác, không có dấu hiệu nào.

Đây là nguyên nhân thật của 7 test fast_v2 "fail có sẵn": chúng fail **local** nhưng
xanh trên **CI**. Chứng minh: vô hiệu hóa việc tìm ngược → **68 test pass**.

Đã sửa: `load_dotenv(ENV_FILE)` và `Settings.env_file` đều trỏ tuyệt đối vào project root.

---

## Giai đoạn 3 — Vector Index contract

| Việc | Nơi |
|---|---|
| Bảng `VectorIndex` + `PaperIndex` | `db_models.py` |
| `EmbeddingIdentity` = (provider, model, dimension); bảng tra dimension; raise khi model lạ | `embedding_manager.py` (mới) |
| Tên collection sinh từ identity, không từ config | `embedding_manager.py` |
| Ghi identity vào Chroma collection metadata; đối chiếu khi mở | `vector_store.py` |
| `recover_vectors_for_paper` dùng identity của instance, không dùng config runtime | `vector_store.py` |
| Vòng đời `PENDING → INDEXING → READY / FAILED`, commit trạng thái **trước** khi ghi vector | `index_registry.py` (mới), `ingestion_service.py` |
| Truyền `ids` tường minh cho Chroma (dùng `chunk_id`) → chống duplicate | `vector_store.py` |
| Bỏ nhánh re-add mỗi lần chạy synthesis | `ingestion_service.py` |
| PDF parse lỗi → `PdfIngestionError`, không âm thầm index abstract | `ingestion_service.py` |
| Structured error `EMBEDDING_INDEX_MISMATCH` (409) và `EMBEDDING_NOT_CONFIGURED` (503) | `main.py` |
| Script re-index có versioning: `--plan` / `--build` / `--promote` / `--drop` | `scripts/reindex_vectors.py` (mới) |
| 16 test giữ contract embedding | `tests/test_services/test_embedding_identity.py` (mới) |

### Điểm cần chú ý khi review

**Tên collection đổi.** Từ `litreview_papers_{provider}_v3` sang
`index_v1_{provider}_{model}_{dimension}`. **Vector cũ sẽ không được tìm thấy** — cần
chạy `python -m scripts.reindex_vectors --build` để dựng lại từ chunk trong Postgres.
Đây là chủ đích: tên cũ nói dối về nội dung bên trong.

**`ensure_paper_ingested` giờ raise.** Trước đây mọi lỗi đều bị nuốt và trả về một
`ingestion_id` hợp lệ. Caller nào đang giả định hàm này không bao giờ lỗi cần được rà lại
khi làm Giai đoạn 5.

**`ready_paper_ids()` đã có nhưng chưa ai gọi.** Việc lọc retrieval theo
`PaperIndex.status == READY` thuộc Giai đoạn 6 (synthesis), chưa nối vào pipeline.

---

## Cố ý hoãn — và lý do

**1. Hợp nhất Alembic (mục 12.3).** Không làm.

Đã kiểm chứng: `alembic upgrade head` **fail ngay** trên SQLite —

```
sqlalchemy.exc.CompileError: (in table 'projects', column 'criteria_include'):
Compiler ... can't render element of type ARRAY
```

Revision đầu vẫn tạo cột `ARRAY` trong khi model đã chuyển sang JSON (có hẳn một
revision tên `align_array_columns_with_json_models` cho thấy việc chuyển đã xảy ra
nhưng revision gốc chưa theo). Chuyển sang Alembic-only lúc này sẽ làm hỏng toàn bộ
dev local. Cần **sinh lại một baseline revision** trước — việc riêng, cần test riêng.

Tạm thời vẫn là `create_all()` + trình vá thủ công, nhưng trình vá **không còn nuốt lỗi**.
Bảng `VectorIndex` / `PaperIndex` mới được `create_all()` tạo bình thường.

**2. Auth cho 50 route còn lại.** Xem phần Giai đoạn 0 ở trên.

**3. Dọn 894 lỗi ruff có sẵn.** CI chạy `ruff check src/ tests/` và **đang đỏ** với
894 lỗi (227 `W293` khoảng trắng, 161 `UP006`, 114 `UP045`, 107 `I001`, 71 `F401`...),
tích tụ vì `ruff>=0.8.0` không pin nên phiên bản mới liên tục thêm rule.
728 lỗi tự sửa được bằng `ruff check --fix`, nhưng đó là một diff cơ học rất lớn
trộn lẫn vào các thay đổi thực chất sẽ không review nổi. **Nên làm thành một commit
riêng, không kèm gì khác.** File tôi động vào đều đã sạch lint.

Trong số đó có 2 lỗi thật đáng chú ý: `F811` bắt được đúng vụ **hai hàm trùng tên
`search_papers_semanticscholar`** trong `scholar_api.py` (audit mục 6.2).

**4. Backend origin vẫn là IP literal trong `vercel.json`.** Vercel rewrite **không nội
suy biến môi trường** — `$BACKEND_ORIGIN` sẽ hỏng ngầm, nên không dùng. Đã gom về đúng
một chỗ duy nhất và ghi rõ cách xử lý ở
[DEPLOY_BACKEND_ORIGIN.md](./DEPLOY_BACKEND_ORIGIN.md). Fix bền vững là Elastic IP
hoặc DNS name — việc hạ tầng, không phải việc code.

---

## Việc vận hành cần làm, không nằm trong code

**Xoay toàn bộ key.** Những thứ sau đã nằm trong lịch sử git công khai và phải coi như đã lộ:

- `SECRET_KEY` cũ: `SUPER_SECRET_KEY_LITREVIEW_AI20K_AGENT_TOKEN_SECRET_KEY_2026`
- `GOOGLE_CLIENT_ID` hardcode trong `auth_routes.py`
- Mọi API key từng xuất hiện trong log hoặc `/health`

Xóa khỏi code không đủ — lịch sử git vẫn còn.

**Production đang chạy với key giả.** `/health` của EC2 trả `"openai_key_prefix":"sk-placeho"`.
Sau nhánh này, trạng thái đó sẽ raise lỗi cấu hình rõ ràng thay vì âm thầm bắn request
thất bại. Cần đặt key thật, hoặc tắt tính năng LLM cho tới khi có.

**Đổi mật khẩu bất kỳ tài khoản `admin123` nào đang tồn tại trong DB.** Nhánh này ngừng
*tạo* tài khoản đó, nhưng không xóa tài khoản đã có.


---

## Giai đoạn 4 — LLM Router

Module mới `src/services/llm/`:

| File | Vai trò |
|---|---|
| `registry.py` | **Nơi duy nhất** chứa tên model. 10 model, kèm context window và khả năng structured output |
| `capability.py` | 20 task khai báo yêu cầu (`json_schema`, `min_context`, `tool_calling`) |
| `credentials.py` | Nhiều key mỗi provider, round-robin xác định, có bí danh; key 429 bị ngưng tạm, key 401 bị vô hiệu |
| `errors.py` | Phân loại `QUOTA` / `AUTH` / `PERMISSION` / `NOT_FOUND` / `BAD_REQUEST` / `TRANSIENT` |
| `router.py` | `select(task)` — capability gate, thứ tự do `LLM_PROVIDER_PRIORITY` |
| `invoker.py` | `ainvoke_with_failover` + `CallBudget` |

Cách dùng, ở mọi nơi:

```python
from src.services.llm import ainvoke_with_failover
result, outcome = await ainvoke_with_failover("generate_criteria", build_runner, messages)
```

Log mỗi lần chọn provider giải thích chính nó:

```
llm.select task=extract_evidence needs=json_schema ctx>=32000
  skipped=groq(no credential configured (GROQ_API_KEY is unset))
  selected=gemini:gemini-2.0-flash key=lien
```

### Chi phí — đo bằng test, không phải ước lượng

| Tình huống | Trước | Sau |
|---|---|---|
| Key sai (401) | tới 24 lệnh gọi tính phí | 1 lệnh gọi mỗi key rồi chuyển |
| Model không tồn tại (404) | tới 24 | **1**, không thử provider khác |
| Không có key nào | vẫn dựng `sk-placeholder`, 24 lệnh gọi | **0** |
| Chạy loạn | không giới hạn | `CallBudget` chặn |

28 test trong `tests/test_services/test_llm_router.py` khẳng định các con số này.

### Cấu hình mới

```env
LLM_PROVIDER_PRIORITY=gemini,groq,openai

# Nhiều key một provider, có bí danh để truy vết log
GEMINI_API_KEYS=lien:AIza...,huyen:AIza...,team:AIza...

# Model tách khỏi credential — đổi key KHÔNG đổi model
GEMINI_MODEL=gemini-2.0-flash
OPENAI_MODEL=gpt-4o-mini
```

Mỗi người đặt `LLM_PROVIDER_PRIORITY` riêng trong `.env` local — không đụng file chung, không conflict khi merge.

### Call site đã chuyển

| File | Trước |
|---|---|
| `criteria_generator.py` | 5 client tự dựng, `keys[1]`, lỗi trả trong `criteria_include` |
| `scope_optimizer.py` | 5 client tự dựng, `keys[0]`, lỗi trả trong `feedback` |
| `project_routes.py` (keywords) | cờ openai-hay-gemini theo tên model, 2 khối parse, lỗi → `[]` |

### Còn lại của Giai đoạn 4

`rag_service.py`, `synthesis_llm_service.py`, `deps_provider.py`, `gap_finder.py` vẫn giữ cascade riêng. Chúng đã nhận bản vá phân loại lỗi ở Giai đoạn 1 nên không còn đốt tiền như trước, nhưng chưa đi qua router. Chuyển từng file một, mỗi file một PR.

---

## Giai đoạn 5 — Toàn vẹn dữ liệu

**Bỏ chỗ bịa quartile Scopus.** `scopus_matcher.py` khi không tìm thấy tạp chí trong bảng nguồn thì đoán `scopus_status="indexed"` và gán `Q1`/`Q2` theo số trích dẫn, kèm comment *"to look professional"*. Docstring của **chính module đó** (dòng 19-24) đã ghi rõ quartile phải luôn là None vì file nguồn Scopus không có cột quartile — cùng kiểu vi phạm như docstring của `build_embeddings`. Giờ trả `undetermined` + quartile None.

Kèm theo: bộ lọc danh sách paper nhận cả `undetermined`, nếu không danh sách sẽ trống — đó chính là lý do heuristic bịa kia ra đời. Hiển thị paper với trạng thái "chưa xác thực" là cách sửa đúng, không phải nhét thứ hạng bịa vào DB.

**Bỏ ID Scopus bịa.** `main.py` seed 24 tạp chí với `sourcerecord_id` tự chế (`"12345678901"` cho PLOS ONE, một dãy MDPI đánh số liên tiếp). Giờ dùng tiền tố `seed:` không thể nhầm với ID Scopus thật, quartile để None.

**Xóa hàm trùng tên.** `scholar_api.py` có hai `search_papers_semanticscholar`; bản sau đè bản trước lúc import. Bản chết có chữ ký `(query, api_key=None, limit=10)` trong khi call site truyền `limit` ở vị trí thứ hai — nếu nó là bản sống thì `limit` sẽ bị nhận làm API key. Cascade 429→OpenAlex của nó đã có sẵn trong `search_papers_auto`.

**`except Exception: pass`**: 55 → 44.

**Structured error** cho `NO_CAPABLE_LLM_PROVIDER` (503), `LLM_BUDGET_EXCEEDED` (429), `PDF_INGESTION_FAILED` (422).

### Còn lại của Giai đoạn 5

- Contract test / Zod validation cho response schema (mục 11.3–11.4) — chưa làm.
- 44 vị trí `except Exception: pass` còn lại chưa rà từng cái.
- 894 lỗi ruff có sẵn vẫn làm CI đỏ — vẫn nên để một commit riêng.
