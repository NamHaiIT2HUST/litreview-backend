# System Contracts — Audit và Kế hoạch chuẩn hóa

**Phạm vi audit:** toàn bộ `src/` (130 file, ~24.8k LOC), `frontend/src/` (52 file, ~21.7k LOC), config deploy, CI, và lịch sử git của `main` / `develop` / `feature/ngaedit-integration`.

**Ngày thực hiện:** 2026-08-26. Commit gốc: `e0e38be` (main), `2afe198` (develop), `752dc8f` (origin/feature/ngaedit-integration).

**Đối tượng đọc:** tech lead — để phân rã thành issue và giao việc.

---

## Mục lục

**Phần I — Audit (bằng chứng)**
- [0. Tóm tắt điều hành](#0-tóm-tắt-điều-hành)
- [1. Environment ↔ Runtime: nguyên nhân "chỉ chạy được phần mình"](#1-environment--runtime)
- [2. Config ↔ Persistent data: embedding không được đối xử như schema](#2-config--persistent-data)
- [3. LLM Runtime: fallback không kiểm soát và cơ chế đốt tiền](#3-llm-runtime)
- [4. Deploy và hạ tầng](#4-deploy-và-hạ-tầng)
- [5. Bảo mật](#5-bảo-mật)
- [6. Các vấn đề toàn vẹn dữ liệu khác](#6-các-vấn-đề-toàn-vẹn-dữ-liệu-khác)
- [7. Bảng ưu tiên](#7-bảng-ưu-tiên)

**Phần II — Thiết kế**
- [8. Nguyên tắc nền](#8-nguyên-tắc-nền)
- [9. Tầng Vector Index (stateful)](#9-tầng-vector-index)
- [10. Tầng LLM Runtime (stateless)](#10-tầng-llm-runtime)
- [11. Tầng API Contract (BE ↔ FE)](#11-tầng-api-contract)
- [12. Chuẩn hóa môi trường](#12-chuẩn-hóa-môi-trường)
- [13. Xây lại Synthesis: contract phải tuân thủ](#13-xây-lại-synthesis)

**Phần III — Thi công**
- [14. Kế hoạch theo giai đoạn](#14-kế-hoạch-theo-giai-đoạn)
- [15. Định nghĩa hoàn thành](#15-định-nghĩa-hoàn-thành)

---
---

# PHẦN I — AUDIT

## 0. Tóm tắt điều hành

Triệu chứng team báo cáo — *"mỗi người làm một tính năng, ghép lại thì lỗi liên tục; kéo code chung về máy thì chỉ chạy được phần mình làm, dù đã dùng chung `.env`; gọi API vẫn trừ tiền nhưng không có output"* — không phải một bug, cũng không phải hệ quả của việc dùng nhiều LLM provider.

Chẩn đoán: **hệ thống thiếu contract rõ ràng ở các boundary có state, nên rất nhiều lỗi bị biến thành "thành công giả"**. Pipeline vẫn chạy, HTTP vẫn 200, DB vẫn có dữ liệu, log vẫn báo success — nhưng dữ liệu hoặc output không còn mang ý nghĩa mà tầng sau đang giả định là nó có.

Ba nhóm boundary đang bị vi phạm:

| Boundary | Contract lẽ ra phải có | Thực trạng |
|---|---|---|
| **Environment ↔ Runtime** | Cùng `.env` → cùng hành vi trên mọi máy | Cùng `.env` cho ra *hai database khác nhau*, *hai vector store khác nhau*, *hai bộ thư viện khác nhau* tùy máy |
| **Config ↔ Persistent data** | Index tạo bằng model nào thì query bằng đúng model đó | Runtime config quyết định model, kể cả khi sửa chữa dữ liệu lịch sử |
| **Producer ↔ Consumer** | Lỗi phải nổi lên thành lỗi | 55 vị trí nuốt exception; nhiều vị trí trả dữ liệu bịa như kết quả thật |

Ngoài ra phát hiện một nhóm vấn đề **bảo mật nghiêm trọng** không nằm trong câu hỏi ban đầu nhưng phải xử lý trước mọi việc khác (mục 5).

---

## 1. Environment ↔ Runtime

Nhóm nguyên nhân này giải thích chính xác triệu chứng team mô tả, và **không liên quan gì đến nội dung `.env`**. Chia sẻ `.env` giống hệt nhau vẫn không giải quyết được.

### 1.1. Dependency Python hoàn toàn không được pin — nghiêm trọng

`requirements.txt` có 56 dòng. **Không một dòng nào dùng `==`.** Tất cả đều `>=`:

```
fastapi>=0.115.0
langchain>=0.3.0
langchain-openai>=0.3.0
langchain-community>=0.3.0
langgraph>=0.2.0
sentence-transformers>=3.0.0
```

Không có `requirements.lock`, không `poetry.lock`, không `pip-tools`, không constraint file.

Người cài môi trường ngày 10/8 và ngày 26/8 nhận **hai bộ thư viện khác nhau**, từ cùng một file, cùng một commit. LangChain có breaking change ở mức minor rất thường xuyên (vị trí import `embeddings`, chữ ký `with_structured_output`, hành vi `Chroma` wrapper đều đã đổi trong dải `0.3.x`).

Đây gần như chắc chắn là nguyên nhân số một của *"code giống nhau mà máy tôi chạy được, máy bạn không"*. Nó cũng khiến CI mất giá trị: CI xanh hôm nay có thể đỏ ngày mai mà không ai commit gì.

Frontend đỡ hơn nhưng vẫn có lỗ: `frontend/package.json` dùng caret range, *có* `package-lock.json`, nhưng cả hai lệnh build đều dùng `npm install` chứ không phải `npm ci`:

- `package.json` (root): `"build": "cd frontend && npm install && npm run build"`
- `vercel.json`: `"buildCommand": "cd frontend && npm install && npm run build"`

### 1.2. Postgres lỗi kết nối thì tự động rơi về SQLite — nghiêm trọng

`src/database.py:138-160`:

```python
async def create_all_tables():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        if "postgresql" in DATABASE_URL or "postgres" in DATABASE_URL:
            print(f"[Database Warning] Không thể kết nối PostgreSQL ({DATABASE_URL}): {e}")
            print("[Database Fallback] Tự động chuyển sang sử dụng SQLite: ...")
            DATABASE_URL = "sqlite+aiosqlite:///./data/app.db"
            engine, AsyncSessionLocal = _get_engine_and_session(DATABASE_URL)
```

Kết hợp `.env.example` dòng 44: `DATABASE_URL=postgresql://postgres:password@localhost:5434/litreview`. Port 5434 chỉ tồn tại khi container `db` trong `docker-compose.yml` đang chạy.

Kịch bản thực tế:

- Thành viên A: `docker compose up db` rồi `make run` → **PostgreSQL**.
- Thành viên B: chỉ `make run` → kết nối 5434 bị từ chối → **âm thầm chuyển sang SQLite** `./data/app.db`.

Cùng `.env`, cùng commit. Nhưng dữ liệu ở hai database khác nhau, schema khác nhau (SQLite không có UUID/JSONB thật), và tính năng của người kia — vốn test trên Postgres — không chạy trên máy B.

Cảnh báo chỉ in bằng `print()`, không qua logger, không có gì trong `/health` cho biết app đang chạy trên database nào.

**Vấn đề phái sinh:** `DATABASE_URL` là biến global bị mutate lúc runtime, nhưng hai module đã import ở top level:

- `src/synthesis/graph.py:9,15` → `synthesis_write_gate = SynthesisWriteGate(DATABASE_URL)`
- `src/tasks/synthesis_tasks.py:9,36` → `checkpoint_dsn = _checkpoint_connection_string(DATABASE_URL)`

Sau khi fallback, hai module này vẫn giữ **chuỗi Postgres cũ đã chết**.

### 1.3. Ba cơ chế quản lý schema chạy song song — nghiêm trọng

Repo có đồng thời:

1. **Alembic** — `alembic.ini` + 8 migration trong `alembic/versions/`.
2. **`Base.metadata.create_all()`** — chạy mỗi lần khởi động (`src/main.py:27`), và thêm lần nữa trong `docker-compose.yml` ở `command` của service `backend`.
3. **`ensure_local_schema_compatibility()`** — `src/database.py:163-248`, trình vá schema tự viết, chạy `ALTER TABLE` thủ công mỗi lần khởi động.

**Không chỗ nào trong repo gọi `alembic upgrade`** — không trong `Makefile`, `docker-compose.yml`, `Dockerfile`, hay CI. 8 migration là code chết.

Vì `create_all()` tạo bảng trực tiếp từ model mà không stamp `alembic_version`, nếu sau này ai chạy `alembic upgrade head` trên DB đã được `create_all()` khởi tạo, Alembic sẽ tưởng DB ở base và cố tạo lại bảng → lỗi.

`ensure_local_schema_compatibility()` còn nuốt toàn bộ lỗi:

```python
def safe_exec(stmt_str: str):
    try:
        sync_conn.execute(text(stmt_str))
    except Exception as e:
        # Ignore duplicate column or already existing errors
        pass
```

Comment nói để bỏ qua lỗi "cột đã tồn tại", nhưng `except Exception: pass` bỏ qua *mọi* lỗi — kể cả lỗi quyền, kiểu dữ liệu, cú pháp. Schema thực tế trên máy mỗi người là trạng thái tích lũy khác nhau.

### 1.4. Chroma cũng bị chia đôi giống database

`src/services/vector_store_config.py`:

```python
def build_chroma_connection_kwargs(settings) -> dict:
    host = (getattr(settings, "chroma_host", "") or "").strip()
    if host:
        return {"host": host, "port": ..., "ssl": ...}
    return {"persist_directory": getattr(settings, "chroma_persist_dir", "./data/chroma")}
```

`.env.example` để `CHROMA_HOST=` rỗng. Nên chạy native dùng Chroma **embedded** (`./data/chroma`, tính theo `os.getcwd()`), chạy Docker Compose dùng **Chroma server**. Hai chế độ không thấy nhau, không có log cho biết đang ở chế độ nào.

Docstring của chính file này ghi rõ *"Production uses client/server mode so the API and Celery worker do not share an embedded persistent store across processes"* — nhưng default lại là embedded, và Celery worker chạy tiến trình riêng.

### 1.5. `.env.example` mâu thuẫn với code và với chính nó

**a) Bật pipeline thử nghiệm làm mặc định.** `.env.example` dòng 30-31:

```
SYNTHESIS_MODE=fast_v2_experimental
FAST_V2_GENERATOR=hosted_api
```

Trong khi `src/config.py:131-138` ghi rõ:

```python
# "legacy" is the ONLY supported production path and MUST stay the default.
# ... That path is EXPERIMENTAL: its generation latency is validated but its
# claim-level factual grounding is NOT. Never make it the default without the
# promotion criteria in that doc.
synthesis_mode: Literal["legacy", "fast_v2_experimental"] = "legacy"
```

Code cố tình đặt `legacy` làm mặc định an toàn, nhưng **bất kỳ ai copy `.env.example` đều đang chạy pipeline thử nghiệm chưa kiểm chứng về grounding**. Hai người, một sửa `.env` một không, chạy hai pipeline synthesis hoàn toàn khác nhau.

**b) Buộc tải model.** `FAST_V2_RERANKER=cross_encoder` ghi đè default an toàn `identity`, vốn tồn tại để *"importing/running fast_v2 (and CI) never downloads a checkpoint"*.

**c) Comment mâu thuẫn giá trị ngay dưới.** Dòng 8-9: *"Synthesis uses Gemini by default"* — nhưng dòng 15 là `SYNTHESIS_LLM_PROVIDER=openai`.

**d) Tham chiếu hạ tầng đã bỏ.** Dòng 27: *"Set FAST_V2_HOSTED_API_KEY in local .env or the Render environment dashboard"* — team đã rời Render từ 25/8.

**e) `CHROMA_PORT` lệch.** `.env.example` ghi `8001`, `config.py:189` default `8000`.

**f) Thiếu biến mà code thực sự đọc:**

| Biến | Đọc tại |
|---|---|
| `SECRET_KEY` | `auth_routes.py:28` |
| `GOOGLE_CLIENT_ID`, `GOOGLE_REDIRECT_URI` | `auth_routes.py:32-39` |
| `SERPAPI_API_KEY` / `SERPAPI_KEY` / `SERP_API_KEY` | `routes.py:251,276`, `deps_provider.py:133` |
| `GEMINI_API_KEYS` (số nhiều) | `config.py:99` |
| `GEMINI_KEY_CRITERIA_GENERATOR`, `GEMINI_KEY_PICO`, `GEMINI_KEY_SCOPE_OPTIMIZER` | `criteria_generator.py:78`, `deps_provider.py:70`, `scope_optimizer.py:81` |
| `DEEPSEEK_API_KEY`, `DEEPSEEK_API_BASE` | `config.py:60,110` |
| `OPENROUTER_API_KEY`, `OPENAI_BASE_URL`, `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`, `LLM_PROVIDER` | `config.py:59-124` |
| `PORT` | `config.py:22` (đọc trước `APP_PORT`, chỉ `APP_PORT` được document) |

**g) Không có `frontend/.env.example`.** Không tồn tại trên bất kỳ nhánh nào. Frontend dùng `VITE_API_BASE` (`apiConfig.js:2`) và `VITE_GOOGLE_CLIENT_ID` (`AuthContext.jsx:206`) nhưng không ai biết hai biến này tồn tại. Đây là lý do trực tiếp khiến giá trị hardcode trong code quyết định mọi người nói chuyện với backend nào.

**h) SerpAPI key có ba tên khác nhau trong code.** `routes.py:251` chỉ đọc `SERPAPI_KEY`; `deps_provider.py:133` chỉ đọc `SERPAPI_API_KEY`; `routes.py:276` đọc cả ba. Set đúng một tên thì một nửa tính năng search hoạt động, nửa kia im lặng nhận chuỗi rỗng.

### 1.6. CI không bảo vệ được gì đáng kể

`.github/workflows/ci.yml` toàn văn: setup Python 3.11 → `pip install -r requirements.txt` → `ruff check` → `pytest`.

Những gì CI **không** làm: không build frontend, không lint/test frontend, không chạy `mypy` (dù `Makefile` có target), không cài dependency có pin, không có contract test, không kiểm tra migration.

CI đặt `OPENAI_API_KEY: test-key` — chuỗi truthy, nên code path kiểm tra "có key hay không" đi vào nhánh "có key" và thử gọi mạng thật bằng key không hợp lệ.

### 1.7. Vấn đề nhỏ hơn nhưng vẫn gây lệch

- `database.py:18` — `os.makedirs("data", exist_ok=True)` chạy **lúc import**, đường dẫn theo `os.getcwd()`.
- `document_processor.py:12` — `UPLOAD_DIR = "uploads/papers"` tương đối theo CWD. Trên EC2 không có volume bền vững, PDF upload mất khi thay instance.
- `docker-compose.yml` — `backend` và `worker` chạy `user: root` và bind-mount `- .:/app`. Trên host Linux, file container tạo thuộc root, developer không xóa được nếu không sudo. Trên Windows không gặp — một nguồn "máy tôi được, máy bạn không" nữa.
- `config.py:25` — `cors_origins` default `http://localhost:3000` nhưng Vite chạy 5173. Xem 5.8: field này thực tế không được dùng ở đâu.

---

## 2. Config ↔ Persistent data

### 2.1. Nguyên tắc bị vi phạm

Embedding model tạo ra **dữ liệu bền vững**. 50.000 vector ghi vào Chroma bằng model A chỉ có nghĩa trong "hệ tọa độ" của model A. Query bằng model B — dù cùng số chiều — là so sánh hai hệ tọa độ không liên quan, kết quả vô nghĩa nhưng *trông như bình thường*.

Vì vậy embedding model phải được quản lý như **schema của database**, không phải như một API provider có thể fallback. LLM generation thì ngược lại: tương đối stateless, đổi provider chỉ ảnh hưởng chất lượng output một request, không hỏng dữ liệu đã lưu.

Code hiện tại đối xử với cả hai như nhau.

### 2.2. `build_embeddings()` fallback câm — nghiêm trọng

`src/services/vector_store.py:80-95`:

```python
if provider == "openai":
    embedding_key = (...)
    if not embedding_key:
        gemini_key = getattr(settings, "effective_gemini_api_key", "") or os.getenv("GEMINI_API_KEY")
        if gemini_key and len(gemini_key) > 20 and not gemini_key.endswith("..."):
            try:
                from langchain_google_genai import GoogleGenerativeAIEmbeddings
                return GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=gemini_key)
            except Exception:
                pass
        from langchain_community.embeddings import FakeEmbeddings
        return FakeEmbeddings(size=1536)
```

Config nói `openai`, nhưng runtime có thể trả Gemini `text-embedding-004` (768 chiều) hoặc `FakeEmbeddings` (vector ngẫu nhiên, không đọc nội dung). Không có `logging.warning` nào trên đường này.

Trong khi `VectorStoreService.__init__` (dòng 172-177) đặt tên collection **theo config, không theo backend thực tế**:

```python
provider_suffix = (getattr(settings, "embedding_provider", "local") or "local").lower()
self.vector_store = Chroma(collection_name=f"litreview_papers_{provider_suffix}_v3", ...)
```

Vector 768 chiều của Gemini, hoặc vector ngẫu nhiên, được ghi vào collection tên `litreview_papers_openai_v3`. **Tên collection nói dối về nội dung của nó.**

### 2.3. Đây là bản vá đúng đã bị ghi đè

Vấn đề này **đã từng được sửa đúng, rồi bị đảo ngược hai ngày sau**:

| Ngày | Commit | Nội dung |
|---|---|---|
| 23/8 07:57 | `5fbc555` | *"fix: stop silently falling back to non-semantic hash embeddings"* — `build_embeddings()` raise rõ ràng khi thiếu key; hash embedding chỉ còn dùng qua opt-in `EMBEDDING_PROVIDER=hash-debug`; thêm `tests/test_services/test_embedding_provider.py` bao phủ hành vi raise |
| 25/8 22:17 | `a07f35a` | *"fix(embeddings): graceful fallback for embedding provider when OpenAI key is absent"* — thay `raise` bằng fallback Gemini rồi `FakeEmbeddings` |
| 25/8 22:25 | `e0e38be` | *"fix(vector_store): safely handle dummy or malformed Gemini keys"* — vá lên trên bản đã sai, không khôi phục `raise` |

Docstring của `build_embeddings()` **vẫn giữ nguyên câu từ bản vá cũ** (dòng 52-56):

> *"Construct the configured embedding backend without silent fallback. Real providers either initialize successfully or raise."*

Docstring nói không có silent fallback; code ngay dưới có silent fallback.

Đây là dữ kiện quan trọng: vấn đề không phải team không biết cách sửa. Team **đã sửa đúng một lần, kèm test**. Nó mất vì không có cơ chế nào chặn việc đảo ngược, và commit message *"graceful fallback"* nghe như cải tiến nên không ai soi lại.

Hệ quả: **`main` hiện tại kém an toàn hơn `develop`** ở đúng hàm này. `develop` vẫn giữ bản raise nghiêm ngặt.

### 2.4. Đội đã từng gặp hậu quả này

`docs/EMBEDDING_MIGRATION_GUIDE.md` — do chính team viết — mô tả đúng lỗi mà 2.1 dự đoán:

> ```
> Collection expecting embedding with dimension of 128, got 1536
> ```
> *"Chroma khóa cứng số chiều theo lần insert đầu tiên của collection... dữ liệu vector cũ của bạn (nếu có) đã luôn vô dụng cho semantic search thật"*

Bài toán "embedding là schema" đã xảy ra một lần trong thực tế, và cách xử lý là **viết hướng dẫn để mỗi người tự xóa Chroma bằng tay**. Không có cơ chế nào trong code ngăn tái diễn. Lần này nó tái diễn ở dạng nguy hiểm hơn: thay vì lỗi cứng "dimension mismatch" (dễ thấy), `FakeEmbeddings` cùng 1536 chiều với OpenAI nên **không gây lỗi gì cả**.

### 2.5. `EMBEDDING_MODEL` dùng chung cho mọi provider

`src/config.py:47-48`:

```python
embedding_model: str = "text-embedding-3-small"
embedding_provider: Literal["local", "gemini", "openai", "hash-debug"] = "openai"
```

`embedding_model` không gắn với provider. Đổi `EMBEDDING_PROVIDER=gemini` mà quên đổi `EMBEDDING_MODEL` sẽ gọi `GoogleGenerativeAIEmbeddings(model="text-embedding-3-small")` — model không tồn tại ở Google.

Quan trọng hơn: **đổi model trong cùng provider cũng phá index**. `text-embedding-3-small` (1536) → `text-embedding-3-large` (3072) là hai không gian vector khác nhau, nhưng `collection_name` chỉ chứa provider suffix, không chứa model. Đổi model cùng provider sẽ ghi tiếp vào **đúng collection cũ**.

### 2.6. `recover_vectors_for_paper()` — vi phạm nguy hiểm nhất

`src/services/vector_store.py:245-288`, gọi tự động từ `search_similar_documents` (dòng 297-301) và `search_similar_documents_with_scores` (dòng 315-319) mỗi khi Chroma không tìm thấy vector:

```python
async def recover_vectors_for_paper(self, paper_id: str):
    """Phục hồi vector từ bảng pdf_chunks trong PostgreSQL lên ChromaDB nếu đĩa ảo bị xóa."""
    ...
    await asyncio.to_thread(self.vector_store.add_documents, documents=documents)
```

`self.vector_store` mang `embedding_function=self.embeddings` — **model đang cấu hình ở runtime hiện tại**, không phải model đã dùng lúc index.

Kịch bản: index 100 PDF bằng OpenAI `text-embedding-3-small` tháng trước. Hôm nay hết tiền, đổi sang Gemini. Ai đó search paper cũ mà Chroma vừa bị dọn cache → recovery chạy, đọc text từ Postgres, **re-embed bằng Gemini**, ghi vào collection đang chứa vector OpenAI.

Vì sao nguy hiểm hơn `FakeEmbeddings`: `FakeEmbeddings` nhìn tên là biết sai. Recovery trông như tính năng reliability tốt. Request không fail. Log in `"Successfully recovered N vectors"`. Dữ liệu có thật. Search vẫn trả kết quả. Chỉ tính đúng đắn ngữ nghĩa đã hỏng.

Toàn bộ hàm bọc trong `try/except` in `print(...)`, nên kể cả Chroma từ chối vì lệch dimension, lỗi cũng bị nuốt.

**Nguyên tắc bị vi phạm:** runtime config không được quyền quyết định model dùng để sửa chữa dữ liệu lịch sử. Metadata của index lịch sử mới có quyền đó.

### 2.7. Không có trạng thái index → partial failure không được ghi nhận

`src/models/db_models.py` — bảng `Paper` có `pdf_status`, `extraction_status`, `scopus_status`, `oa_status`, `coverage_year_status`, nhưng **không có trường nào theo dõi trạng thái embedding/index**.

`src/services/ingestion_service.py:151-164`:

```python
if paper.file_path and os.path.exists(paper.file_path):
    try:
        pages, chunks = processor.extract_and_chunk(paper.file_path)
        if chunks and any(c.page_content.strip() for c in chunks):
            ingestion_id = await persist_pdf_provenance(...)   # set active_ingestion_id
            await vector_store_service.stage_documents_for_paper(str(paper.id), chunks)
            await db.commit()
            return ingestion_id
```

`persist_pdf_provenance` (dòng 106-108) đặt `paper.active_ingestion_id` **trước khi** vector được ghi. `stage_documents_for_paper` (`vector_store.py:209-213`) nuốt mọi exception và trả `[]`. Sau đó `db.commit()` chạy vô điều kiện.

Nếu embedding API hết quota giữa chừng: **DB ghi nhận paper ingest thành công, Chroma không có vector nào**. Không trạng thái nào phân biệt. Lần search sau sẽ kích hoạt `recover_vectors_for_paper`, tạo thêm một tầng sai nữa.

### 2.8. Duplicate vector tích lũy mỗi lần chạy synthesis

`src/services/ingestion_service.py:119-142`:

```python
if paper.active_ingestion_id is not None:
    try:
        existing_chunks = (await db.execute(select(PDFChunk).where(PDFChunk.paper_id == paper.id))).scalars().all()
        if existing_chunks:
            docs = [Document(page_content=c.chunk_text, metadata={...}) for c in existing_chunks]
            await vector_store_service.add_documents(docs)
    except Exception:
        pass
    return paper.active_ingestion_id
```

Mỗi lần `ensure_paper_ingested` được gọi cho paper **đã** có `active_ingestion_id`, nó đọc lại toàn bộ chunk và gọi `add_documents` — không phải `stage_documents_for_paper`, không xóa gì trước.

`Chroma.add_documents` không truyền `ids` sẽ sinh UUID mới mỗi lần. **Cùng một chunk được insert lại mỗi lần chạy synthesis.** Sau N lần chạy, mỗi chunk có N bản sao.

- Storage phình tuyến tính theo số lần chạy.
- Retrieval lệch: top-k trả nhiều bản sao cùng một đoạn, đẩy đoạn khác ra khỏi kết quả. Chất lượng evidence giảm dần theo số lần chạy, âm thầm.

`metadata` bản re-add cũng nghèo hơn bản gốc (thiếu `source`, `paper_title`, `ingestion_id`, offset) — chính là triệu chứng commit `7ec0862` từng cố sửa.

### 2.9. PDF parse thất bại được chuyển thành "ingest thành công"

`src/services/ingestion_service.py:165-203`:

```python
    except Exception as e:
        print(f"Warning: Failed PDF re-ingestion for '{paper.title}': {e}")

# Fallback for metadata / search paper (or unparseable PDF)
abstract_text = (paper.abstract or "").strip()
if len(abstract_text) < 10:
    abstract_text = f"Title: {paper.title}. No detailed abstract provided."
...
ingestion_id = await persist_pdf_provenance(
    db=db, paper=paper, pages=[page], chunks=[chunk],
    parser_metadata={"parser_name": "metadata_fallback", ...}
)
```

Người dùng upload PDF 30 trang. Parse lỗi (scan, encrypted, layout lạ) → exception in ra rồi **rơi xuống nhánh fallback**, tạo một "chunk" chứa tiêu đề + abstract, ghi vào DB như ingestion hợp lệ, trả `ingestion_id` như thành công.

Synthesis sau đó trích dẫn paper này như đã đọc toàn văn, trong khi bằng chứng thực tế chỉ là abstract. Với sản phẩm literature review, đây là vấn đề toàn vẹn học thuật.

Tệ hơn: khi không có abstract, hệ thống bịa chuỗi `"Title: X. No detailed abstract provided."` và **index chính chuỗi đó làm nội dung trích dẫn được**.

Điểm cứu vãn: `parser_name` ghi `"metadata_fallback"` trong `PageText`, về lý thuyết truy vết được. Nhưng không chỗ nào trong pipeline synthesis hay UI đọc trường này để cảnh báo.

---

## 3. LLM Runtime

### 3.1. Quy mô vấn đề, đo bằng số

```
16  tên model hardcode rải rác trong src/
 5  base URL hardcode
 8  bản logic cascade chọn provider viết độc lập
12  task LLM, tất cả đều cần structured output
 0  chỗ khai báo task nào cần capability gì
```

Tên model hardcode (đếm bằng grep trên `src/`):

| Lần | Model |
|---|---|
| 9 | `gemini-flash-lite-latest` |
| 8 | `llama-3.3-70b-versatile` |
| 8 | `deepseek/deepseek-v3.2` |
| 7 | `gpt-4o-mini` |
| 6 | `gemini-flash-latest` |
| 6 | `gemini-3.5-flash-lite` |
| 3 | `gemini-2.0-flash` |
| 2 | `text-embedding-3-small` |
| 1 mỗi loại | `gpt-4o`, `gemini-1.5-flash`, `deepseek-chat`, `deepseek-v3`, `claude-opus-5-thinking`, `models/text-embedding-004` |

Base URL: `api.openai.com/v1` (2), `openrouter.ai/api/v1` (3), `api.xkiro.com/v1` (2), `api.deepseek.com/v1` (1), `api.groq.com/openai/v1` (1).

Cascade nhân bản ở 8 nơi, thứ tự và model khác nhau:

| File | Cascade |
|---|---|
| `rag_service.py:251-341` | auto-detect → Gemini → Groq → OpenAI-compatible |
| `synthesis_llm_service.py:44-107` | Groq → Gemini → OpenAI-compatible |
| `synthesis_llm_service.py:198-297` | 6 candidate runner |
| `deps_provider.py:70-89` | Gemini → Groq → OpenAI |
| `criteria_generator.py:74-118` | 3 model Gemini → Groq → OpenAI → synthesis service |
| `gap_finder.py:198-242` | tương tự |
| `scope_optimizer.py:77-121` | tương tự |
| `project_routes.py:368-420` | OpenAI hoặc Gemini theo cờ `use_openai` |

Đổi một nhà cung cấp không phải sửa một chỗ, mà là **truy 16 chuỗi trên 8 file**. Đây là lý do cấu trúc khiến "fix bằng AI vẫn không triệt để" — AI sửa file đang mở, bảy bản sao còn lại vẫn nguyên.

### 3.2. Provider bị suy ra từ định dạng API key

`src/config.py:55-66` gộp mọi key vào một property:

```python
@property
def effective_openai_api_key(self) -> str:
    return (
        self.openai_api_key or self.llm_api_key
        or self.deepseek_api_key or self.openrouter_api_key
        or os.getenv("OPENAI_API_KEY", "") ...
    ).strip()
```

Một key DeepSeek được trả về dưới tên `effective_openai_api_key`.

`src/config.py:102-129` suy ra endpoint từ **prefix key**:

```python
if key.startswith("sk-or-v1-"):  return "https://openrouter.ai/api/v1"
if key.startswith("sk-xt-"):     return "https://api.xkiro.com/v1"
```

`src/config.py:77-84` viết lại cả **tên model** theo prefix key:

```python
if key and key.startswith("sk-xt-"):
    if model in ["deepseek-chat", "deepseek", "deepseek-v3", "gpt-4o-mini", "gpt-4o"]:
        return "deepseek/deepseek-v3.2"
```

Hệ quả với thao tác hằng ngày:

```
Dán key mới vào .env
     ↓
prefix khớp pattern nào?
     ├─ khớp   →  provider + base URL + tên model đều đổi theo, không báo
     └─ không khớp  →  base URL = ""  →  client mặc định gọi api.openai.com
                        bằng key của nhà cung cấp khác  →  401
```

Trường hợp "không khớp" xảy ra với key proxy nội bộ, key doanh nghiệp, key nhà cung cấp mới, hoặc khi OpenAI đổi định dạng key. Triệu chứng (401) không chỉ về nguyên nhân (base URL sai).

### 3.3. Cơ chế đốt tiền — tính được chính xác

`_get_runner_candidates()` (`synthesis_llm_service.py:198-297`) dựng tối đa **6 runner** cho một lệnh gọi structured-output:

1. `primary.with_structured_output(schema)`
2. `primary.with_structured_output(schema, method="json_mode")`
3. `primary.with_structured_output(schema, method="function_calling")`
4. `UniversalJsonRunner(primary, schema)` — nhét JSON schema vào system prompt (prompt dài hơn = nhiều input token hơn)
5. `ChatOpenAI(model="gpt-4o-mini", ...)` — hardcode
6. `ChatGoogleGenerativeAI(model="gemini-2.0-flash", ...)` — hardcode

`_invoke_structured()` (dòng 300-352):

```python
for attempt in range(len(self._retry_delays) + 1):   # _retry_delays = (1.0, 2.0, 4.0) → 4 vòng
    for model_tag, runner in candidates:              # tối đa 6
        try:
            return await runner.ainvoke(messages)
        except Exception as exc:
            if _is_transient_provider_error(exc):
                continue
            else:
                raise exc
```

`_is_transient_provider_error` (dòng 110-136):

```python
if status_code in (400, 401, 403, 404, 409, 422, 429) or (isinstance(status_code, int) and status_code >= 500):
    return True
```

**401 (key sai), 403 (không quyền), 404 (model không tồn tại), 400/422 (request sai) đều bị phân loại là lỗi tạm thời.** Đây đều là lỗi vĩnh viễn — retry không bao giờ thành công.

```
1 bước synthesis, key sai:
  6 candidate × 4 attempt  =  24 lệnh gọi tính phí
  × 12 task × số dimension × 15 papers
  =  hàng trăm lệnh gọi, 0 output
```

Tình huống này **đang xảy ra trên production**: `/health` của EC2 trả `"openai_key_prefix":"sk-placeho"`.

Nguyên nhân gốc, `synthesis_llm_service.py:96-97`:

```python
"model": model_name or "claude-opus-5-thinking",   # tên model Anthropic gửi tới endpoint OpenAI-compatible
"api_key": openai_key or "sk-placeholder",         # không key vẫn dựng client
```

Điểm tích cực: mọi lần thử đều ghi vào `LLMCallLog` (dòng 318-338) kèm `model_name`, `attempt`, `status`, `error`. Dữ liệu kiểm chứng con số trên đã có sẵn trong DB.

### 3.4. Model được cấu hình bị thay thế âm thầm

`synthesis_llm_service.py:76`:

```python
if provider == "gemini" or (not openai_key and gemini_key):
```

Config nói `SYNTHESIS_LLM_PROVIDER=openai`, nhưng không có OpenAI key mà có Gemini key → **tự chuyển sang Gemini**, không log.

Tên model cũng bị ghi đè (dòng 67, 85):

```python
g_model = model_name if model_name and not model_name.startswith("gpt-") else "llama-3.3-70b-versatile"
g_model = model_name if (model_name and model_name.startswith("gemini-") and "2.0" not in model_name and "1.5" not in model_name) else "gemini-flash-lite-latest"
```

Đặt `SYNTHESIS_MODEL=gpt-4o` rồi provider rơi sang Groq → model thực tế `llama-3.3-70b-versatile`. Giá trị `.env` bị bỏ qua hoàn toàn.

Fallback sang model khác không chỉ đổi chất lượng — nó đổi cả khả năng hỗ trợ structured output, kích thước context, định dạng prompt. Cả 12 task LLM đều gọi qua `_invoke_structured`, tức **tất cả đều yêu cầu structured output**, nhưng không chỗ nào khai báo yêu cầu đó.

**6 candidate ở 3.3 không phải tính năng chịu lỗi — nó là triệu chứng của việc thiếu khai báo capability.** Code phải thử-sai lúc chạy vì không ai nói trước model nào hỗ trợ gì.

### 3.5. Lỗi được trả về dưới dạng dữ liệu hợp lệ

`src/agents/slr_swarm/agents/criteria_generator.py:139-150`:

```python
if "429" in error_str or "quota" in error_str or "rate limit" in error_str:
    return CriteriaGenerationResult(
        criteria_include=["⚠️ Hệ thống đang tạm thời hết hạn mức AI (Quota Exceeded). Vui lòng thử lại sau 1-2 phút."],
        criteria_exclude=["⚠️ Vui lòng cấu hình thêm API Key hoặc thử lại sau ít phút."]
    )
```

Thông báo lỗi nhét vào **đúng trường dành cho tiêu chí lựa chọn nghiên cứu**. Hàm trả `CriteriaGenerationResult` hợp lệ về kiểu. HTTP 200. Frontend hiển thị chuỗi này như một inclusion criterion. Người dùng bấm lưu thì chuỗi vào DB và có thể xuất ra báo cáo PRISMA.

Đây là ví dụ rõ nhất trong repo cho *silent contract violation*: lỗi không biến mất, nó cải trang thành dữ liệu.

### 3.6. Không truy được key nào tốn tiền

`src/config.py:86-95`:

```python
@property
def effective_gemini_api_key(self) -> str:
    import random
    ...
    if aiza_tokens:
        return random.choice(aiza_tokens)
```

`random.choice` chạy **mỗi lần property được đọc**. Hai lần gọi liên tiếp trong cùng request có thể dùng hai key thuộc hai Google project khác nhau. Không quy được trách nhiệm chi phí, không tái lập được lỗi.

Các agent SLR-swarm còn đánh chỉ số key **theo vị trí**: `criteria_generator.py:78` dùng `keys[1]`, `gap_finder.py:202` dùng `keys[2]`, `scope_optimizer.py:81` dùng `keys[0]`. Không gì đảm bảo thứ tự trong `GEMINI_API_KEYS` giống nhau giữa các máy.

### 3.7. Bảng tổng hợp: vì sao "đổi key/provider" hiện là thao tác nguy hiểm

| Thao tác team làm thường xuyên | Hệ quả trong code hiện tại |
|---|---|
| Đổi key OpenAI A → key OpenAI B | An toàn (may mắn — cùng prefix) |
| Đổi key OpenAI → key DeepSeek | Base URL, tên model **đổi ngầm** theo prefix |
| Dán key có prefix lạ | Base URL rỗng → gọi nhầm `api.openai.com` → 401 |
| Xóa key hết tiền khỏi `.env` | Provider **tự nhảy** sang provider khác, không log |
| Đặt `SYNTHESIS_MODEL` | Có thể bị ghi đè âm thầm |
| Key hết quota giữa chừng | 24 lệnh gọi tính phí trước khi bỏ cuộc |
| Nhiều key Gemini để xoay vòng | `random.choice`, không biết key nào chạy |

### 3.8. Thống kê nuốt lỗi

`grep -rn "except Exception:" src/ -A1 | grep -c "pass"` → **55 vị trí** `except Exception: pass`.

Tập trung dày nhất ở `src/agents/slr_swarm/agents/` (criteria_generator, gap_finder, scope_optimizer — mỗi file 4 vị trí) và `deps_provider.py`.

---

## 4. Deploy và hạ tầng

### 4.1. Lịch sử chuyển deploy target

Truy vết qua `git log --all -- frontend/src/utils/apiConfig.js vercel.json Procfile src/config.py`:

| Thời điểm | Commit | Target |
|---|---|---|
| trước 17/8 | — | chỉ localhost; `apiConfig.js` chưa tồn tại |
| 17/8 15:28 | `677270c` | **Render** — `https://litreview-backend-5u4q.onrender.com` |
| 25/8 00:37 | `84a574b` | **Railway** — `https://litreview-backend-production-0298.up.railway.app` |
| 25/8 13:11 | `bed66da` | **AWS EC2** `18.143.200.110` — frontend chuyển sang path tương đối, `vercel.json` thêm rewrite proxy |
| 25/8 22:03 | `9d7bfc5` | **AWS EC2** `13.212.121.28` — IP đổi lần nữa, cùng ngày |

IP đổi hai lần trong một ngày cho thấy instance dùng **IP động, không phải Elastic IP**. Sẽ đổi tiếp mỗi lần stop/start, mỗi lần cần một commit sửa `vercel.json` + `apiConfig.js`.

Kiểm tra trực tiếp lúc audit:

- Render → **không phản hồi** (timeout).
- Railway → 200, `{"env":"development","model_name":"deepseek/deepseek-v3.2"}`.
- EC2 → 200, `{"env":"production","openai_key_prefix":"sk-placeho","model_name":""}`.

### 4.2. `develop` và `feature/ngaedit-integration` trỏ vào hạ tầng đã bỏ

`git merge-base --is-ancestor` xác nhận `84a574b`…`9d7bfc5` chỉ tồn tại trên `main`. Trên hai nhánh còn lại:

- `vercel.json` **không có rewrite backend nào** (chỉ SPA catch-all). Deploy Vercel từ `develop` sẽ không proxy `/api/v1/*`.
- `apiConfig.js` vẫn fallback cross-origin sang Railway.

Railway còn sống nên "vẫn chạy được", nhưng là hạ tầng bị bỏ rơi, không ai theo dõi.

Đây là câu trả lời cho "kéo code chung về máy thì chỉ chạy được phần mình": hai người ở hai nhánh đang nói chuyện với **hai backend khác nhau, hai database khác nhau**.

`origin/feature/ngaedit-integration` (HEAD `752dc8f`) thực chất là tổ tiên của `main`, đã merge qua `cac86ac` — ảnh chụp đông cứng, không nên dùng làm tham chiếu.

### 4.3. Fallback trong `safeFetch` không thể hoạt động trên production

`frontend/src/utils/apiConfig.js:41-52`:

```javascript
const fallbackUrl = `http://13.212.121.28:8000/api/v1${path}`;
try { return await fetch(fallbackUrl, options); } ...
```

Site production trên Vercel chạy HTTPS. Fallback gọi `http://` — **mixed active content, bị trình duyệt chặn**. Đường dẫn này không bao giờ chạy được từ production. Code trông giống cơ chế chịu lỗi nhưng thực tế vô hiệu.

Backend EC2 cũng phục vụ qua HTTP trần, không TLS. Vercel rewrite che được với trình duyệt, nhưng chặng Vercel → EC2 vẫn plaintext qua Internet công cộng.

### 4.4. `safeFetch` chỉ dùng ở một nửa codebase

- 24 lời gọi `safeFetch(...)`
- 25 lời gọi `fetch(...)` trực tiếp (dùng hằng `API_BASE`)
- chỉ 36 chỗ kiểm `.ok` trên tổng 49 lời gọi

`API_BASE` là hằng tính một lần lúc import, nên base URL vẫn nhất quán. Nhưng nửa dùng `fetch` trực tiếp không có retry/fallback, và có chỗ nhận response 4xx/5xx rồi xử lý như thành công.

---

## 5. Bảo mật

Nhóm này không nằm trong câu hỏi ban đầu, nhưng mức độ đủ nghiêm trọng để ưu tiên tuyệt đối.

### 5.1. 56 route API, 0 route có xác thực

```
grep -rn "@router\.(get|post|put|delete|patch)" src/api/ | wc -l   →  56
grep -rn "Depends(get_current_user)|Depends(require_admin)" src/api/ | wc -l   →  0
```

Không tồn tại `get_current_user`, không có `HTTPBearer`, không có dependency xác thực nào trong toàn bộ `src/api/`.

`jwt.encode` được gọi ở `auth_routes.py:68`. `jwt.decode` chỉ xuất hiện **đúng một lần** trong toàn repo: `src/api/project_routes.py:72`, và chỉ để *phân loại* trả project của ai:

```python
def _extract_user_info(authorization, x_user_id):
    if authorization and authorization.startswith("Bearer "):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            ...
        except Exception:
            pass                      # token sai → bỏ qua, đi tiếp
    if x_user_id:
        try:
            return UUID(str(x_user_id)), "user"    # tin header thô, không xác thực
        except Exception:
            pass
    return None, None
```

Header `X-User-Id` được chấp nhận làm danh tính **không xác thực gì**. Bất kỳ ai cũng đọc/sửa được dữ liệu người khác bằng cách đặt một header.

### 5.2. Endpoint admin không được bảo vệ

- `auth_routes.py:170` — `GET /auth/admin/stats`: không có dependency xác thực. Trả danh sách toàn bộ user.
- `auth_routes.py:219` — `DELETE /auth/admin/users/{user_id}`: không có dependency xác thực. Ai gọi được cũng xóa được user bất kỳ (trừ role admin).

Cả hai đang mở công khai trên `13.212.121.28:8000` và qua Vercel rewrite.

### 5.3. Tài khoản admin mặc định seed mỗi lần khởi động

`src/main.py:141-165`:

```python
async def _ensure_default_admin():
    """Seed the default admin account (admin123 / 123) if no admin exists."""
    admin_user = User(username="admin123", hashed_password=hash_password("123"), role=Role.admin)
```

Chạy trong `lifespan`, mỗi lần khởi động, mọi môi trường kể cả production.

### 5.4. `SECRET_KEY` có giá trị dự phòng hardcode

`src/api/auth_routes.py:28`:

```python
SECRET_KEY = os.getenv("SECRET_KEY", "SUPER_SECRET_KEY_LITREVIEW_AI20K_AGENT_TOKEN_SECRET_KEY_2026")
```

`SECRET_KEY` không có trong `.env.example`, nên khả năng cao chưa ai set. Chuỗi này nằm trong repo — ai đọc được repo đều ký được JWT hợp lệ.

Kết hợp 5.1 + 5.3 + 5.4: chiếm quyền admin trên production là việc tầm thường.

### 5.5. `POST /auth/google` trả danh tính không xác thực

`src/api/auth_routes.py:241-284`:

```python
async def verify_google_auth(payload: GoogleAuthPayload):
    user_email = payload.email          # lấy thẳng từ client
    if payload.access_token:
        try:
            res = await client.get("https://www.googleapis.com/oauth2/v3/userinfo", ...)
            if res.status_code == 200:
                user_email = google_info.get("email", user_email)
        except Exception as e:
            logger.warning(...)          # lỗi → giữ nguyên email do client cung cấp
    if not user_email:
        user_email = "scholar.researcher@gmail.com"
    return UserProfileResponse(...)
```

Ba lỗ hổng chồng nhau:

1. Không có token nào cũng không sao — `payload.email` do client tự khai được dùng luôn.
2. Gọi Google thất bại cũng không sao — không có nhánh `else: raise`.
3. Không có gì cả thì bịa `scholar.researcher@gmail.com` và trả profile như đăng nhập thành công.

Endpoint không phát JWT, nhưng frontend coi response là bằng chứng đăng nhập (`AuthContext.jsx:45-53` lưu vào localStorage). Kết hợp 5.1 — backend không kiểm token ở đâu — thì toàn bộ xác thực chỉ tồn tại ở client. `AuthContext.jsx:175` còn lưu `litreview_local_users` (danh sách tài khoản) vào localStorage.

### 5.6. `google_oauth_callback` là stub trỏ vào localhost

`src/api/auth_routes.py:314-325` nhận authorization code nhưng **không đổi lấy token**, chỉ log rồi `RedirectResponse(url="http://localhost:5173/#overview")`. Code path này không hoạt động ở bất kỳ môi trường deploy nào. `GOOGLE_CLIENT_ID` cũng có giá trị hardcode thật ở dòng 32-35.

### 5.7. `/health` công khai rò rỉ thông tin cấu hình

`src/main.py:195-203` trả `gemini_key_prefix` và `openai_key_prefix` (10 ký tự đầu), không yêu cầu xác thực. Đây là cách audit này phát hiện production đang chạy `sk-placeho`.

### 5.8. CORS mở toàn bộ, và setting CORS là cấu hình chết

`src/main.py:174-180`:

```python
settings = get_settings()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, ...)
```

`settings` được lấy ra nhưng `settings.cors_origins` **không dùng ở đâu cả**. `CORS_ORIGINS` trong `.env.example` là biến không có tác dụng — contract violation ở tầng config.

---

## 6. Các vấn đề toàn vẹn dữ liệu khác

### 6.1. Danh mục pattern "thành công giả"

| Vị trí | Hành vi | Hệ quả |
|---|---|---|
| `vector_store.py:94-95` | thiếu key → `FakeEmbeddings` | vector ngẫu nhiên, tốn storage, retrieval vô nghĩa |
| `vector_store.py:87-93` | thiếu key → Gemini embeddings | trộn không gian vector trong collection tên "openai" |
| `vector_store.py:187-189` | `add_documents` lỗi → `return 0` | mất vector im lặng |
| `vector_store.py:245-288` | recovery dùng model runtime | trộn hai hệ tọa độ trong một collection |
| `ingestion_service.py:140-141` | `except Exception: pass` | lỗi re-index bị nuốt |
| `ingestion_service.py:165-203` | PDF parse lỗi → index abstract | trích dẫn paper như đã đọc toàn văn |
| `ingestion_service.py:170-171` | thiếu abstract → bịa nội dung | chuỗi bịa thành evidence trích dẫn được |
| `ingestion_service.py:198-201` | staging lỗi → `pass`, vẫn commit | DB nói ingested, Chroma rỗng |
| `criteria_generator.py:139-150` | lỗi LLM → trả lỗi trong trường dữ liệu | thông báo lỗi thành inclusion criteria |
| `synthesis_llm_service.py:97` | không key → `sk-placeholder` | 24 request thất bại thay vì fail-fast |
| `synthesis_llm_service.py:110-136` | 401/403/404/400/422 = transient | retry lỗi vĩnh viễn, đốt token |
| `database.py:149-158` | Postgres lỗi → SQLite | dữ liệu vào DB khác, chỉ `print()` |
| `database.py:172-177` | `safe_exec` nuốt mọi lỗi ALTER | schema khác nhau giữa các máy |
| `auth_routes.py:281-284` | thiếu token → user bịa | bypass xác thực |
| `main.py:174-180` | `cors_origins` không được dùng | cấu hình chết |
| `scopus_matcher.py:224-246` | không có trong bảng Scopus → đoán quartile theo tên nhà xuất bản | dữ liệu bịa trình bày như dữ liệu Scopus thật |
| `main.py:52-110` | seed 20 journal hardcode với `sourcerecord_id` bịa (`"12345678901"` cho PLOS ONE) | dữ liệu tham chiếu giả làm nguồn xác thực |
| `project_routes.py:368-420` | lỗi sinh keyword → `keywords = []` | không phân biệt "không kết quả" với "gọi API lỗi" |
| `search_service.py:9-30` | SerpAPI lỗi → `return 0` | như trên |
| `apiConfig.js:41-52` | fallback HTTP từ trang HTTPS | cơ chế chịu lỗi không bao giờ chạy |

### 6.2. Hai hàm trùng tên trong cùng module

`src/services/scholar_api.py` định nghĩa `search_papers_semanticscholar` hai lần: dòng 242 và 470. Định nghĩa thứ hai ghi đè thứ nhất lúc import. Toàn bộ logic bản đầu (xử lý 429 → fallback OpenAlex, raise 401/403) là code chết; bản chạy thật chỉ `print` cảnh báo rồi `return []`.

### 6.3. Chi phí gọi API học thuật nhân lên

`scholar_api.py:345-467` — `search_papers_serpapi` với mỗi kết quả gọi thêm 3 API làm giàu (CrossRef + OpenAlex + Semantic Scholar) qua `asyncio.gather`. Với `limit` kết quả: `1 + limit×3` request ra ngoài. SerpAPI là dịch vụ tính phí.

`search_papers_auto` (dòng 601-633) thử tuần tự tối đa 4 nhà cung cấp nếu các bước trước rỗng hoặc lỗi.

### 6.4. Endpoint gửi log ra dịch vụ bên ngoài

`.env.example` khai `AI_LOG_SERVER=https://ai-logs.note.transformerlabs.ai/api/ingest`, kèm `Makefile` target `log-sync` chạy `scripts/log_antigravity.py` và `scripts/submit_log.py`. Cần xác nhận nội dung gì đang gửi ra endpoint bên thứ ba này, đặc biệt nếu log chứa prompt, nội dung paper, hoặc thông tin cấu hình.

---

## 7. Bảng ưu tiên

Xếp theo mức thiệt hại nếu không xử lý, không theo độ khó.

### P0 — xử lý ngay, trước mọi việc khác

| # | Vấn đề | Vị trí |
|---|---|---|
| 1 | 56 route không có xác thực; `X-User-Id` được tin vô điều kiện | `src/api/*` |
| 2 | Endpoint admin (`stats`, `delete user`) mở công khai | `auth_routes.py:170,219` |
| 3 | Admin `admin123`/`123` seed mỗi lần khởi động, kể cả production | `main.py:141-165` |
| 4 | `SECRET_KEY` hardcode trong repo | `auth_routes.py:28` |
| 5 | `/auth/google` trả danh tính không xác thực | `auth_routes.py:241-284` |
| 6 | Production đang chạy `sk-placeho` — mọi lệnh gọi LLM thất bại sau 24 lần thử | `/health` của EC2 |

### P1 — chặn thất thoát tiền và hỏng dữ liệu

| # | Vấn đề | Vị trí |
|---|---|---|
| 7 | `FakeEmbeddings` / Gemini fallback câm | `vector_store.py:80-95` |
| 8 | `recover_vectors_for_paper` dùng model runtime sửa dữ liệu lịch sử | `vector_store.py:245-288` |
| 9 | 401/403/404/400/422 bị coi là transient → retry đốt token | `synthesis_llm_service.py:110-136` |
| 10 | 6 candidate × 4 attempt = 24 lệnh gọi tính phí cho một bước | `synthesis_llm_service.py:198-352` |
| 11 | `sk-placeholder` thay vì fail-fast | `synthesis_llm_service.py:97` |
| 12 | Không có trạng thái index → partial failure ghi nhận là thành công | `ingestion_service.py:151-164` |
| 13 | Duplicate vector tích lũy mỗi lần chạy synthesis | `ingestion_service.py:119-142` |
| 14 | PDF parse lỗi → index abstract như thể toàn văn | `ingestion_service.py:165-203` |

### P2 — chặn "chạy máy này không chạy máy kia"

| # | Vấn đề | Vị trí |
|---|---|---|
| 15 | Dependency Python không pin, không lockfile | `requirements.txt` |
| 16 | Postgres lỗi → SQLite âm thầm | `database.py:149-158` |
| 17 | Ba cơ chế schema song song; Alembic là code chết | `database.py`, `main.py`, `alembic/` |
| 18 | `.env.example` bật `fast_v2_experimental` trái default an toàn của code | `.env.example:30` |
| 19 | `develop`/`ngaedit` trỏ Railway; `main` trỏ EC2 IP động | `apiConfig.js`, `vercel.json` |
| 20 | Không có `frontend/.env.example`; `VITE_*` không được document | — |
| 21 | Chroma embedded vs server chia đôi theo máy | `vector_store_config.py` |
| 22 | `npm install` thay vì `npm ci` trong build | `package.json`, `vercel.json` |

### P3 — nợ kỹ thuật cần dọn để không tái phát

| # | Vấn đề |
|---|---|
| 23 | Cascade provider nhân bản ở 8 nơi |
| 24 | Credentials / Provider / Model trộn làm một; provider suy ra từ prefix key |
| 25 | 55 vị trí `except Exception: pass` |
| 26 | CI không build frontend, không typecheck, không contract test |
| 27 | `cors_origins` là cấu hình chết; CORS mở `*` |
| 28 | `scopus_matcher` đoán quartile; `main.py` seed `sourcerecord_id` bịa |
| 29 | Hai hàm trùng tên trong `scholar_api.py` |
| 30 | `random.choice` chọn Gemini key → không truy vết được chi phí |

---
---

# PHẦN II — THIẾT KẾ

## 8. Nguyên tắc nền

Toàn bộ thiết kế phục vụ đúng một quy tắc. Quy tắc này nên đưa vào `CLAUDE.md` / coding convention và áp cho mọi PR:

> **Không được "graceful fallback" nếu fallback làm thay đổi ý nghĩa của dữ liệu, hoặc khiến hệ thống trả ra output trông đúng nhưng thực chất không đáng tin.**
>
> Hệ quả trực tiếp:
> - Lỗi phải nổi lên thành lỗi. Không nhét thông báo lỗi vào trường dữ liệu.
> - `return []` / `return 0` / `return None` phải phân biệt được "không có kết quả" với "gọi thất bại".
> - Runtime config không được quyền quyết định cách sửa chữa dữ liệu lịch sử.
> - Fail-fast ở tầng logic; graceful recovery ở tầng UX. Không đảo ngược hai vế.

Ba tầng contract cần khóa:

```
                 SYSTEM CONTRACTS

        ┌────────────┼──────────────┐
        │            │              │
        ▼            ▼              ▼
   LLM Runtime   Vector Index    API Contract
   (stateless)   (stateful)      (interface)
        │            │              │
   fallback OK   KHÔNG fallback  schema khóa
   + capability  model khóa theo  hai chiều
     gate          index          BE ↔ FE
```

**Phân biệt cốt lõi — LLM và Embedding không cùng loại tài nguyên:**

| | LLM / Generation | Embedding |
|---|---|---|
| Tính chất | tương đối stateless | tạo dữ liệu bền vững |
| Đổi provider giữa chừng | được, chỉ đổi chất lượng output | **không được**, phá không gian vector |
| Key chết | fallback sang provider khác nếu capability cho phép | báo lỗi, dừng |
| Đổi model | được, per-request | phải **re-index** |
| Quản lý như | cấu hình runtime | **schema của database** |

**Ba tầng cấu hình phải tách rời** — đây là mấu chốt cho nhu cầu "mỗi người dùng key riêng, thay key liên tục vì hết tiền":

```
Credentials  →  Provider  →  Model
```

```
OpenAI (provider)
├── key_lien      (hết tiền)
├── key_huyen
└── key_team
        │
        └──►  text-embedding-3-small (model)

Đổi key_lien → key_huyen:  KHÔNG cần re-index (model không đổi)
Đổi OpenAI/text-embedding-3-small → Gemini/embedding-001:  PHẢI re-index
```

Đổi credential là chuyện vận hành, làm thoải mái. Đổi provider/model là thay đổi hành vi hệ thống — với LLM thì được phép (có capability gate), với embedding thì phải qua migration.

---

## 9. Tầng Vector Index

### 9.1. Mô hình dữ liệu

Embedding thuộc về **một lần index**, không thuộc về paper. Một paper có thể tồn tại trong nhiều index qua thời gian:

```
paper A
├─ index v1: OpenAI / text-embedding-3-small / 1536
├─ index v2: Gemini / embedding-001 / 768
└─ index v3: OpenAI / text-embedding-3-large / 3072
```

Vì vậy **không** thêm `Paper.embedding_provider` / `Paper.embedding_model`. Ownership đúng là hai bảng:

```
VectorIndex                      PaperIndex
- id                             - paper_id        (FK Paper)
- collection_name  (unique)      - vector_index_id (FK VectorIndex)
- provider                       - status          (PENDING|INDEXING|READY|FAILED)
- model                          - chunk_count
- dimension                      - error_message
- version         (int)          - indexed_at
- status          (BUILDING|ACTIVE|DEPRECATED)
- created_at
```

`collection_name` sinh từ identity, không phải từ config runtime:

```
index_v{version}_{provider}_{model_slug}
ví dụ: index_v1_openai_text-embedding-3-small
       index_v2_gemini_embedding-001
```

MVP có thể gộp `PaperIndex` sau, nhưng `VectorIndex` phải có ngay — lưu identity vào `Paper` thì mọi migration/re-index sau này phải sửa schema lại.

### 9.2. Postgres là control plane, Chroma là data plane

Không chọn một trong hai làm nguồn sự thật duy nhất:

```
Postgres  =  control plane / source of truth
             (audit, migration, admin UI, biết paper nào ở index nào)

Chroma    =  data plane + self-description
             (collection metadata mô tả chính nó)
```

Khi mở collection, hai bên phải khớp:

```
DB nói:                        Chroma metadata nói:
  index_v4                       provider=openai
  provider=openai                model=text-embedding-3-small
  model=text-embedding-3-small   dimension=1536
  dimension=1536

  không khớp  →  raise EmbeddingIndexMismatch
```

Chroma hỗ trợ collection metadata; ghi identity vào đó lúc tạo, đọc và đối chiếu lúc mở.

### 9.3. Module `src/services/embedding_manager.py`

```python
class EmbeddingIdentity(NamedTuple):
    provider: str          # openai | gemini | local
    model: str
    dimension: int

def resolve_runtime_identity(settings) -> EmbeddingIdentity:
    """Đọc EMBEDDING_PROVIDER + EMBEDDING_MODEL. Không cascade, không đoán."""

def build_embeddings_for(identity: EmbeddingIdentity, credentials) -> Embeddings:
    """Dựng backend đúng theo identity. Thiếu key -> raise. Không fallback provider."""

def verify_collection_lock(index: VectorIndex, chroma_metadata: dict, runtime: EmbeddingIdentity) -> None:
    """Đối chiếu 3 chiều: DB / Chroma metadata / runtime. Lệch -> raise EmbeddingIndexMismatch."""
```

Quy tắc bắt buộc:

- **Không có nhánh fallback provider nào trong production path.** Thiếu key → `raise`.
- `FakeEmbeddings` / `LightweightHashEmbeddings` chỉ tồn tại trong `tests/`. Không import trong `src/services/` ở nhánh production. (`EMBEDDING_PROVIDER=hash-debug` có thể giữ như opt-in tường minh — bản `5fbc555` đã làm đúng cách này.)
- `EMBEDDING_MODEL` phải validate theo provider **lúc khởi động**, không đợi lúc gọi API.
- `dimension` không được suy đoán — lấy từ bảng tra theo (provider, model), hoặc đo một lần lúc tạo index rồi ghi vào `VectorIndex`.

### 9.4. Sửa `recover_vectors_for_paper`

Đây là thay đổi tư duy quan trọng nhất của tầng này:

```
hiện tại:
  không có vector  →  tự tạo lại bằng self.embeddings (runtime config)

phải đổi thành:
  không có vector
    →  tra VectorIndex manifest của paper đó
    →  dựng đúng model của index đó
    →  credentials tương ứng còn dùng được?
          có   → recover
          không → PaperIndex.status = FAILED, raise NEEDS_REINDEX
```

Ghi thành comment trong code, vì đây là invariant dễ bị vô tình phá lại:

> Runtime config không quyết định model dùng để sửa chữa dữ liệu lịch sử. Metadata của index lịch sử mới quyết định.

Đồng thời bỏ `try/except` bao ngoài đang nuốt lỗi (`vector_store.py:287-288`).

### 9.5. Trạng thái index và partial failure

```
PENDING  →  INDEXING  →  READY
                    └─→  FAILED
```

Chỉ `READY` mới được đưa vào RAG/synthesis. Thứ tự ghi phải đảo lại:

```
hiện tại (sai):
  persist_pdf_provenance()      # set active_ingestion_id
  stage_documents_for_paper()   # nuốt lỗi, trả []
  db.commit()                   # commit vô điều kiện

đúng:
  PaperIndex.status = INDEXING;  commit
  persist chunks vào Postgres
  ghi vector vào Chroma          # lỗi -> status = FAILED + error_message, raise
  PaperIndex.status = READY;     chunk_count = N;  commit
```

`vector_store.add_documents` không được `return 0` khi lỗi — phải raise để caller đặt được `FAILED`.

### 9.6. Chống duplicate

1. **Bỏ hẳn nhánh re-add ở `ingestion_service.py:119-142`.** Nếu `active_ingestion_id` đã có và `PaperIndex.status == READY`, không đụng vào Chroma. Việc "cache miss thì phục hồi" là trách nhiệm của `recover_vectors_for_paper` đã sửa ở 9.4.
2. **Truyền `ids` tường minh cho Chroma.** Dùng `chunk_id` từ Postgres làm Chroma document id — insert lại cùng id là upsert, không sinh bản sao.

### 9.7. Re-index có versioning

Đổi model embedding là **migration**, không phải fallback:

```
index_v1_openai_small  (ACTIVE)
        │
        ├─ tạo index_v2_gemini_001  (BUILDING)
        │  build toàn bộ paper từ Postgres chunk text
        │
        ├─ build xong & verify  →  v2 = ACTIVE, v1 = DEPRECATED
        │
        └─ sau thời gian giữ an toàn  →  xóa v1
```

Không xóa index đang phục vụ rồi mới bắt đầu build cái mới. Cần script/CLI `scripts/reindex.py` chạy thủ công, và một endpoint admin gọi được từ UI.

### 9.8. Lỗi cứng ở logic layer, graceful ở UX layer

Backend trả structured error, không trả `[]`, không giả thành công:

```json
{
  "error_code": "EMBEDDING_INDEX_MISMATCH",
  "message": "Collection index_v1_openai_text-embedding-3-small được tạo bằng openai/text-embedding-3-small (1536), runtime hiện tại là gemini/embedding-001 (768).",
  "required_action": "REINDEX",
  "details": { "index_id": "...", "expected": {...}, "actual": {...} }
}
```

Frontend không hiện stack trace hay `500 Internal Server Error`, mà dịch `error_code` thành hành động:

```
Tài liệu này đang dùng embedding index không tương thích
với cấu hình hiện tại.

[Re-index]        ← chỉ hiện với admin
```

*Fail-fast ở tầng logic* và *trải nghiệm tốt ở tầng UX* không mâu thuẫn nhau. Cái phải tránh là **graceful fake success ở tầng logic**.

---

## 10. Tầng LLM Runtime

### 10.1. Cấu trúc `.env` đích

Mỗi người tự cấu hình trong `.env` **local**, không đụng code, không conflict khi merge:

```env
# ---- Thứ tự ưu tiên provider (mỗi người tự đặt theo key mình có) ----
LLM_PROVIDER_PRIORITY=gemini,groq,openai

# ---- Credentials: mỗi provider một biến riêng, KHÔNG gộp ----
GEMINI_API_KEY=AIza...
GROQ_API_KEY=gsk_...
OPENAI_API_KEY=sk-proj-...
DEEPSEEK_API_KEY=
OPENROUTER_API_KEY=
XKIRO_API_KEY=

# ---- Model: tách khỏi credential, KHÔNG suy ra từ prefix key ----
GEMINI_MODEL=gemini-2.0-flash
GROQ_MODEL=llama-3.3-70b-versatile
OPENAI_MODEL=gpt-4o-mini

# ---- Base URL: tường minh, chỉ cần khi dùng proxy/self-host ----
OPENAI_BASE_URL=
DEEPSEEK_BASE_URL=
```

Ba tính chất quan trọng:

1. **Không biến nào gộp nhiều provider.** Bỏ `LLM_API_KEY`, `effective_openai_api_key`, `MODEL_NAME` dùng chung.
2. **Không suy đoán gì từ prefix key.** Prefix chỉ dùng để *cảnh báo* khi có vẻ sai, không dùng để *quyết định*.
3. **Thứ tự ưu tiên là cấu hình của từng người**, nằm trong `.env` local — hai người dùng thứ tự khác nhau không tạo diff nào trong git.

### 10.2. Nhiều key cho một provider (giải quyết bài "key hết tiền")

```env
# Nhiều key cho cùng một provider, có bí danh để truy vết
GEMINI_API_KEYS=lien:AIza...,huyen:AIza...,team:AIza...
```

Quy tắc:

- **Round-robin có thứ tự xác định**, không `random.choice`. Cùng input → cùng key → lỗi tái lập được.
- Key trả 429 (hết quota) hoặc 401 (chết) được **đánh dấu tạm ngưng** trong bộ nhớ tiến trình kèm thời điểm hết ngưng, không thử lại ngay trong cùng request.
- Mọi log ghi **bí danh** (`lien`, `huyen`, `team`), **không bao giờ ghi giá trị key**.
- Hết key khả dụng của một provider → chuyển provider tiếp theo trong `LLM_PROVIDER_PRIORITY`. Hết provider → raise.
- **Bỏ hoàn toàn** cách đánh chỉ số theo vị trí (`keys[0]`, `keys[1]`, `keys[2]`) trong các agent SLR-swarm. Nếu một agent thật sự cần key riêng, đặt biến có tên rõ ràng và ghi vào `.env.example`.

Điểm mấu chốt: **xoay key trong cùng provider+model không đụng gì tới vector index**. Đây là chỗ mô hình ba tầng trả cổ tức — trước đây đổi key có thể kéo theo đổi model ngầm, mà đổi model embedding thì phá index.

### 10.3. Provider Registry

Một nơi duy nhất mô tả mọi nhà cung cấp. Thay thế 16 tên model và 5 base URL rải rác.

```python
# src/services/llm/registry.py

@dataclass(frozen=True)
class ModelProfile:
    provider: str
    model: str
    base_url: str | None          # None = endpoint mặc định của SDK
    context_window: int
    supports_json_schema: bool    # with_structured_output(schema) chạy được
    supports_json_mode: bool
    supports_function_calling: bool
    supports_tool_calling: bool
    cost_tier: int                # 1 = rẻ nhất, để sắp thứ tự khi ngang capability

MODEL_REGISTRY: dict[str, ModelProfile] = {
    "openai:gpt-4o-mini": ModelProfile(
        provider="openai", model="gpt-4o-mini",
        base_url=None, context_window=128_000,
        supports_json_schema=True, supports_json_mode=True,
        supports_function_calling=True, supports_tool_calling=True,
        cost_tier=1,
    ),
    "gemini:gemini-2.0-flash": ModelProfile(...),
    "groq:llama-3.3-70b-versatile": ModelProfile(...),
    "deepseek:deepseek-v3.2": ModelProfile(...),
}
```

Quy tắc bắt buộc:

- **Không tên model nào được viết literal ngoài file này.** CI thêm kiểm tra chặn regex tên model xuất hiện trong `src/` ngoài `registry.py`.
- Model không có trong registry → **raise lúc khởi động**, không đợi lúc gọi API.
- Thêm nhà cung cấp mới = thêm entry vào registry + thêm biến credential. **Không sửa file nào khác.** Đây là tiêu chí nghiệm thu của thiết kế này.

Registry phải điền từ tài liệu chính thức của từng nhà cung cấp, không đoán. Với endpoint OpenAI-compatible do bên thứ ba vận hành (xkiro, OpenRouter), capability phải **kiểm chứng thực tế một lần** rồi ghi vào registry — proxy thường không hỗ trợ đủ như bản gốc, và đó chính là lý do lịch sử sinh ra `UniversalJsonRunner`.

### 10.4. Task Registry và Capability Gate

```python
@dataclass(frozen=True)
class LLMCapability:
    json_schema: bool = False
    min_context: int = 8_000
    tool_calling: bool = False

TASK_REGISTRY: dict[str, LLMCapability] = {
    "extract_evidence":             LLMCapability(json_schema=True, min_context=32_000),
    "extract_paper_evidence_batch": LLMCapability(json_schema=True, min_context=64_000),
    "propose_claims":               LLMCapability(json_schema=True, min_context=32_000),
    "verify_entailment":            LLMCapability(json_schema=True, min_context=8_000),
    "verify_claim_set":             LLMCapability(json_schema=True, min_context=32_000),
    "verify_claim_set_batch":       LLMCapability(json_schema=True, min_context=64_000),
    "build_outline":                LLMCapability(json_schema=True, min_context=32_000),
    "draft_section":                LLMCapability(json_schema=True, min_context=32_000),
    "refine_section":               LLMCapability(json_schema=True, min_context=32_000),
    "qa_review_batch":              LLMCapability(json_schema=True, min_context=32_000),
    "deduplicate_evidence_batch":   LLMCapability(json_schema=True, min_context=32_000),
    "generate_criteria":            LLMCapability(json_schema=True, min_context=8_000),
    "generate_keywords":            LLMCapability(json_schema=True, min_context=8_000),
    "rag_chat":                     LLMCapability(json_schema=False, min_context=32_000),
}
```

`min_context` phải tính từ prompt thật (evidence context của `extract_evidence` rất dài), không đặt bừa. Bước đầu có thể đo bằng cách log độ dài prompt thực tế trong một tuần.

Thuật toán chọn:

```
get_llm(task="extract_evidence")
    │
    ├─ capability = TASK_REGISTRY[task]
    │
    ├─ với mỗi provider theo LLM_PROVIDER_PRIORITY:
    │     ├─ có credential khả dụng (chưa bị ngưng)?  không → bỏ qua, log lý do
    │     ├─ profile = MODEL_REGISTRY[provider:model]
    │     ├─ profile đáp ứng ĐỦ capability?           không → bỏ qua, log lý do
    │     └─ đủ  →  chọn, log quyết định, trả về client
    │
    └─ không provider nào đủ  →  raise NoCapableProviderError
                                  (liệt kê từng provider và lý do bị loại)
```

Điểm khác biệt cốt lõi: **fallback bị chặn bởi capability, không phải fallback tự do**.

```
Gemini hết quota
    ↓
Groq  →  llama-3.3-70b-versatile hỗ trợ json_schema? context đủ 32k?
           ├─ đủ    →  dùng
           └─ thiếu →  bỏ qua, sang provider kế
    ↓
OpenAI → ...
    ↓
hết provider  →  LỖI RÕ RÀNG, không hạ chuẩn im lặng
```

Bỏ bước capability gate thì fallback sang model không hỗ trợ structured output sẽ rơi vào đúng bẫy **"không crash nhưng output sai"** — cùng họ với `FakeEmbeddings`.

Hệ quả: giảm candidate từ 6 xuống ≤2.

| | Hiện tại | Sau thiết kế |
|---|---|---|
| Số candidate | 6 | ≤2 (phương thức đúng theo profile + `UniversalJsonRunner` làm lưới an toàn cuối) |
| Chọn phương thức | thử lần lượt tới khi chạy | tra `supports_json_schema` / `supports_json_mode` trong registry |
| Fallback provider | 2 model hardcode trong hàm | theo `LLM_PROVIDER_PRIORITY` của người dùng |

Giữ `UniversalJsonRunner` là hợp lý — nó tồn tại vì proxy bên thứ ba hay không hỗ trợ đủ. Nhưng phải là **lưới an toàn cuối cùng có log cảnh báo**, không phải một trong sáu thứ được thử bình thường.

### 10.5. Phân loại lỗi và quy tắc chuyển provider

| Mã lỗi | Bản chất | Hành động đúng |
|---|---|---|
| 400, 422 | request sai định dạng | **Dừng ngay.** Lỗi của ta, đổi provider không giúp gì. |
| 401 | key sai/hết hạn | **Đánh dấu key chết**, thử key kế *cùng provider*; hết key → provider kế. Không retry cùng key. |
| 403 | không có quyền dùng model | **Bỏ qua provider này**, sang provider kế. Không retry. |
| 404 | model không tồn tại | **Dừng ngay.** Cấu hình sai, phải sửa `.env`/registry. |
| 429 | hết quota / rate limit | **Ngưng key này tạm thời**, sang key/provider kế. Không retry ngay cùng key. |
| 408, 409, 5xx | lỗi tạm thời thật | Retry có backoff, tối đa N lần, **cùng provider**. |
| timeout mạng | tạm thời | như trên |

Tác động định lượng:

```
Trường hợp key sai (401):
  hiện tại:  6 candidate × 4 attempt  =  24 lệnh gọi tính phí
  sau sửa:   1 lệnh gọi → 401 → thử key kế → hết key → provider kế
             → hết provider → raise.  Tối đa = số key khả dụng.

Trường hợp không có key nào:
  hiện tại:  vẫn dựng client với "sk-placeholder" → 24 lệnh gọi
  sau sửa:   0 lệnh gọi. Raise lúc khởi tạo.

Trường hợp model không tồn tại (404):
  hiện tại:  24 lệnh gọi
  sau sửa:   0 lệnh gọi — chặn ngay lúc boot bởi kiểm tra registry.
```

Thêm **ngân sách per-session**: giới hạn cứng số lệnh gọi LLM cho một synthesis session; vượt ngưỡng thì dừng, trả structured error. Ngưỡng đặt dựa trên dữ liệu thật từ `LLMCallLog`.

### 10.6. Quan sát chi phí

`LLMCallLog` đã ghi `model_name`, `attempt`, `status`, `duration_ms`, `error`, `prompt_json`, `response_json`. Cần bổ sung:

| Trường thêm | Mục đích |
|---|---|
| `provider` | hiện chỉ có model tag |
| `key_alias` | biết **key nào** tốn tiền (bí danh, không phải key) |
| `task` | biết task nào tốn nhất |
| `input_tokens`, `output_tokens` | tính chi phí thật |
| `selection_reason` | vì sao provider này được chọn, provider trước bị loại vì gì |

Mỗi lần router chọn provider, ghi một dòng:

```
llm.select task=extract_evidence capability=json_schema,ctx>=32k
  skipped=gemini(key lien: quota_exhausted_until=14:32)
  skipped=groq(context_window 8k < 32k)
  selected=openai:gpt-4o-mini key=team
```

### 10.7. Cấu trúc module

```
src/services/llm/
├── __init__.py          # export get_llm()
├── registry.py          # MODEL_REGISTRY — nơi DUY NHẤT có tên model
├── capability.py        # LLMCapability, TASK_REGISTRY
├── credentials.py       # đọc key theo provider, round-robin, đánh dấu ngưng
├── errors.py            # phân loại permanent/transient, exception types
├── router.py            # get_llm(task=...) — thuật toán chọn
└── observability.py     # ghi LLMCallLog, log quyết định chọn provider
```

Mọi call site đổi thành:

```python
from src.services.llm import get_llm
llm = get_llm(task="extract_evidence")
```

Không còn `if provider == ...` ở bất kỳ đâu ngoài `router.py`.

### 10.8. Các thao tác vận hành sau khi có thiết kế này

Đây là phần nghiệm thu thực tế — những việc team làm hằng tuần phải trở nên tầm thường:

| Tình huống | Thao tác | Ảnh hưởng |
|---|---|---|
| Key OpenAI hết tiền, có key OpenAI khác | Thay giá trị trong `OPENAI_API_KEYS` | Không gì cả. Không re-index, không sửa code. |
| Hết tiền OpenAI, muốn chuyển sang Gemini cho LLM | Đổi `LLM_PROVIDER_PRIORITY=gemini,...` | LLM đổi provider. **Embedding không đổi** (biến riêng). Không re-index. |
| Mỗi người muốn dùng provider khác nhau | Mỗi người tự đặt `LLM_PROVIDER_PRIORITY` trong `.env` local | Không diff git, không conflict khi merge. |
| Thêm nhà cung cấp mới | 1 entry vào `MODEL_REGISTRY` + 1 biến credential | Không sửa file nào khác. |
| Muốn 1 agent dùng key riêng | Đặt biến có tên rõ ràng, khai vào `.env.example` | Không đánh chỉ số theo vị trí. |
| Key giữa chừng hết quota | Tự động: ngưng key đó, chuyển key/provider kế, có log | Không có 24 lệnh gọi lãng phí. |
| **Đổi embedding provider/model** | **Phải re-index** — xem 9.7 | Đây là migration, không phải đổi cấu hình. |

Dòng cuối là ranh giới cần nhấn với cả team: **LLM đổi thoải mái, embedding thì không.** Hai thứ này phải nằm ở hai nhóm biến môi trường tách bạch, có comment giải thích rõ trong `.env.example`.

---

## 11. Tầng API Contract

### 11.1. Hiện trạng

Đã kiểm tra hai endpoint tải trọng cao nhất: `GET /synthesis-sessions/{id}` và `POST /projects/{id}/search`. **Cả hai khớp chính xác** giữa Pydantic response model và code frontend đọc field (kể cả cấp lồng `sections[].sentences[].citation_ids`).

Nói rõ: hiện **chưa tìm thấy mismatch thật**. Rủi ro không nằm ở "đang lệch", mà ở chỗ **sự khớp này đang được giữ bằng kỷ luật đặt tên, không có cơ chế nào chặn được lệch trong tương lai**. Một PR đổi `result` thành `synthesis_result` sẽ đi qua CI xanh và chỉ lộ ra khi mở UI.

Đây cũng là tầng duy nhất trong ba tầng có thể chặn được **ở CI**, trước khi merge. Hai tầng kia chỉ chặn được lúc runtime.

### 11.2. Năm lớp cần kiểm khi truy vết "backend có output nhưng UI trắng"

```
1. Backend producer   →  response thật là gì?
2. API schema         →  Pydantic/OpenAPI khai báo gì?
3. HTTP client        →  fetch/safeFetch unwrap thế nào?
4. Frontend state     →  store/hook giữ field nào?
5. Renderer           →  component đọc field nào?
```

Lỗi ở bất kỳ mắt xích nào đều cho cùng một triệu chứng. Dùng khung này khi debug, đừng dừng ở "API trả gì".

### 11.3. Contract test

Test backend hiện dừng ở `assert response.status_code == 200`. Chưa đủ:

```python
data = response.json()
assert "sections" in data
assert data["sections"][0]["sentences"][0]["text"]
assert data["sections"][0]["sentences"][0]["citation_ids"]
```

Hoặc mạnh hơn — snapshot toàn bộ JSON schema của response và fail khi schema đổi mà snapshot chưa cập nhật có chủ đích.

### 11.4. Sinh type cho frontend từ OpenAPI

Đích lý tưởng: `FastAPI → openapi.json → generate frontend types → build fail khi lệch`.

Vướng mắc thực tế: `frontend/` đang là **JavaScript thuần** (52 file `.jsx`/`.js`, không TypeScript), nên không có bước typecheck nào để fail. Hai lựa chọn:

| Phương án | Ưu | Nhược |
|---|---|---|
| **A. Zod (hoặc tương đương) runtime validation** | không cần chuyển TS; validate ngay tại `safeFetch`; lệch schema báo lỗi rõ tại chỗ gọi | chỉ phát hiện lúc chạy, không phải lúc build |
| **B. Chuyển dần sang TypeScript + `openapi-typescript`** | lệch schema làm **build fail** — đúng mục tiêu chặn ở CI | chi phí chuyển đổi lớn với 21.7k LOC |

Khuyến nghị: **A trước, B sau**. Zod schema sinh từ `openapi.json` cho các endpoint quan trọng nhất (synthesis, search, project) là bước rẻ, làm được ngay, bắt được phần lớn rủi ro. Chuyển TS làm dần theo module.

### 11.5. Chuẩn hóa lời gọi HTTP ở frontend

- Mọi lời gọi đi qua **một** client duy nhất (hiện 24 chỗ `safeFetch`, 25 chỗ `fetch` trực tiếp).
- Client đó chịu trách nhiệm: resolve base URL, kiểm `res.ok`, parse structured error (`error_code`), validate schema. Không để mỗi component tự xử lý.
- **Bỏ fallback HTTP hardcode trong `safeFetch`** (`apiConfig.js:41-52`) — bị trình duyệt chặn vì mixed content, không bao giờ chạy được từ production.

---

## 12. Chuẩn hóa môi trường

Không có phần này thì cả ba tầng trên đều vô nghĩa: contract chỉ có ý nghĩa khi mọi người chạy cùng một hệ thống.

### 12.1. Pin dependency

- Sinh `requirements.lock` (pip-tools / `uv pip compile`) từ `requirements.txt`, commit vào repo. CI và Docker cài từ lock.
- Đổi `npm install` → `npm ci` ở cả `package.json` và `vercel.json`.

Riêng việc này đã giải quyết một phần lớn "cùng code, khác hành vi".

### 12.2. Bỏ mọi silent fallback ở tầng hạ tầng

- **Bỏ** fallback Postgres → SQLite (`database.py:149-158`). Không kết nối được DB đã cấu hình thì **dừng khởi động** với thông báo rõ. Muốn chạy SQLite thì đặt `DATABASE_URL=sqlite:///...` tường minh.
- Sửa `DATABASE_URL` thành biến cục bộ, không phải global bị mutate (kéo theo sửa `src/synthesis/graph.py:9,15` và `src/tasks/synthesis_tasks.py:9,36`).
- **Bỏ** `except Exception: pass` trong `safe_exec` (`database.py:172-177`) — hoặc bỏ luôn cả hàm, xem 12.3.
- Chroma: nếu `CHROMA_HOST` rỗng, log **cảnh báo rõ** rằng đang chạy embedded single-process, và **cấm** chế độ này khi có Celery worker.

### 12.3. Một cơ chế schema duy nhất

Chọn **Alembic** làm nguồn duy nhất:

- Bỏ `Base.metadata.create_all()` khỏi startup (`main.py:27`) và khỏi `docker-compose.yml` command.
- Bỏ `ensure_local_schema_compatibility()`; những `ALTER TABLE` trong đó chuyển thành migration Alembic thật.
- Thêm `alembic upgrade head` vào quy trình khởi động (entrypoint container / `make migrate`) và vào CI.
- Với DB hiện có đã được `create_all()` khởi tạo: cần một bước `alembic stamp` một lần cho từng máy, kèm hướng dẫn.

### 12.4. Viết lại `.env.example`

- **Giá trị mặc định phải khớp default an toàn của code.** `SYNTHESIS_MODE=legacy`, `FAST_V2_RERANKER=identity` — hiện đang ngược lại và khiến cả team chạy pipeline thử nghiệm mà không biết.
- Bổ sung đủ mọi biến code thực sự đọc (danh sách ở 1.5f).
- Thống nhất **một tên duy nhất** cho SerpAPI key (`SERPAPI_API_KEY`), sửa cả 3 chỗ đọc trong code.
- Xóa comment mâu thuẫn / tham chiếu Render đã bỏ.
- Ghi rõ `CHROMA_PORT` khác nhau giữa host (8001) và trong container (8000).
- Tạo **`frontend/.env.example`** với `VITE_API_BASE`, `VITE_GOOGLE_CLIENT_ID` và giải thích.
- Tách rõ hai nhóm biến: **LLM (đổi thoải mái)** và **Embedding (đổi phải re-index)**, có comment cảnh báo.

### 12.5. Một nguồn duy nhất cho backend URL

- Bỏ IP hardcode khỏi `frontend/src/utils/apiConfig.js` (dòng 14 và 47) và `vercel.json`.
- `VITE_API_BASE` bắt buộc cho production build — thiếu thì **build fail**, không im lặng dùng giá trị đoán.
- Đồng bộ `vercel.json` giữa các nhánh; `develop` hiện không có rewrite backend nào.
- Hạ tầng: dùng **Elastic IP hoặc domain** thay cho IP EC2 động. Cân nhắc đặt TLS trước backend — chặng Vercel → EC2 hiện là plaintext.

### 12.6. CI phải bảo vệ được các contract

Bổ sung vào `.github/workflows/ci.yml`:

- cài từ `requirements.lock`
- `mypy src/` (target đã có trong `Makefile`)
- build frontend (`npm ci && npm run build`) + `oxlint`
- contract test (11.3)
- **test giữ hành vi fail-fast**: khẳng định `build_embeddings` raise khi thiếu key, `create_synthesis_llm` raise khi không provider nào khả dụng, `recover_vectors_for_paper` raise khi model lệch.

Điểm cuối quan trọng nhất về quy trình. Bản vá `5fbc555` ngày 23/8 đã sửa đúng vấn đề `FakeEmbeddings` **kèm test**, nhưng vẫn bị `a07f35a` đảo ngược hai ngày sau. Cần đảm bảo các test này thực sự chạy trong CI trên **mọi** nhánh.

---

## 13. Xây lại Synthesis

### 13.1. Bối cảnh phải biết trước khi quyết định đập

Repo đã có **hai** bản synthesis, không phải một:

```
legacy:   synthesis_service.py + graph.py + 8 policy  ≈ 3.400 LOC (đang chạy prod)
fast_v2:  src/synthesis/fast_v2/, 37 file             = 5.889 LOC (sau feature flag)
tổng:                                                   9.348 LOC
```

`fast_v2` **không phải code nháp**. Nó có `docs/architecture/FAST_SYNTHESIS_V2.md` — ADR 419 dòng, ghi rõ thành phần nào đóng băng, thành phần nào chưa giải quyết, và **8 tiêu chí thăng cấp**. Chất lượng tài liệu cao hơn mặt bằng repo.

Nó kẹt ở hai chỗ, ADR ghi thẳng ở mục L:

> 1. **Claim-level factual grounding.** `ClaimGroundingService` mới chỉ là interface. Bản hiện thực duy nhất là `UnvalidatedClaimGroundingPassthrough`, luôn báo `claim_grounding_status="unvalidated"` và không bao giờ trả `grounded=true`.
> 2. **General question decomposition.** fast_v2 yêu cầu dimension khai báo sẵn. Cố tình **không** có heuristic biến research question bất kỳ thành dimension.

Đây là **hai bài toán nghiên cứu, không phải kỹ thuật**. Bản viết lại thứ ba sẽ gặp lại đúng hai bài toán này ở đúng chỗ đó.

**Kết luận thẳng:**

- Nếu "siêu tệ" nghĩa là **chất lượng output** (claim sai, trích dẫn sai, review lan man) → viết lại kiến trúc **không giải quyết được**, nghẽn nằm ở tầng phương pháp.
- Nếu "siêu tệ" nghĩa là **code không đọc/sửa/test nổi** → viết lại hợp lý.

Cần xác định rõ lý do trước.

**Cảnh báo vận hành:** `.env.example` đang đặt `SYNTHESIS_MODE=fast_v2_experimental`, trái default an toàn của code. Có thể một phần team đang chạy fast_v2 mà không biết, nên đánh giá "synthesis tệ" hiện có thể đang nói về **hai hệ thống khác nhau tuỳ máy**. Cần thống nhất và đo lại trên cùng pipeline trước khi kết luận.

### 13.2. Chẩn đoán legacy: vấn đề là kích thước hàm, không phải kiến trúc

`src/services/synthesis_service.py` — 1.762 dòng, class `SynthesisService` với 18 method. Lớn nhất:

| Method | Dòng | Độ dài |
|---|---|---|
| `extract_paper_evidence` | 179–418 | 239 |
| `cross_paper_analysis` | 958–1167 | 209 |
| `finalize_review` | 1563–1753 | 190 |
| `_extract_generic_paper_evidence` | 570–742 | 172 |
| `_extract_custom_paper_evidence_batch` | 418–570 | 152 |
| `qa_drafted_review` | 1420–1563 | 143 |

Một method 239 dòng làm nhiều việc cùng lúc: gọi LLM, kiểm grounding, ghi DB, xử lý lỗi, cập nhật coverage. Không test được từng phần, không sửa được một phần mà không sợ vỡ phần khác.

Nhưng cần công bằng: **phần kiến trúc đã tách khá tốt**:

- 8 policy module riêng: `claim_verification_policy.py`, `evidence_extraction_policy.py`, `evidence_deduplication_policy.py`, `outline_coverage_policy.py`, `research_question_policy.py`, `synthesis_coverage_policy.py`, `synthesis_qa_policy.py`, `synthesis_write_gate.py`.
- Orchestration nằm riêng trong LangGraph (`src/synthesis/graph.py`), 9 node, luồng rõ ràng:

```
prepare → [extract_paper × N papers, song song]
        → ensure_coverage → deduplicate_evidence → cross_paper
        → build_outline → [draft_section × M sections, song song]
        → qa_review → finalize
```

Luồng này hợp lý cho một evidence-first pipeline. **Vấn đề nằm trong ruột từng node, không nằm ở hình dạng luồng.** Nghĩa là phần lớn giá trị của "viết lại" đạt được bằng cách **chẻ nhỏ 6 method khổng lồ**, giữ nguyên graph và policy — rẻ hơn nhiều, rủi ro thấp hơn nhiều.

### 13.3. Chất lượng synthesis bị chặn trên bởi chất lượng evidence

Những vấn đề sau **sẽ theo sang bản mới nếu không xử lý riêng**:

- `vector_store.py:94-95` — evidence nền có thể là vector rác (`FakeEmbeddings`).
- `ingestion_service.py:165-203` — evidence nền có thể chỉ là abstract, không phải toàn văn.
- `ingestion_service.py:119-142` — corpus đầy bản sao, retrieval lệch dần.

Trước khi đập, cần trả lời được bằng số: *bao nhiêu phần trăm paper trong DB được index bằng embedding thật, từ toàn văn, không trùng lặp?* Câu hỏi này hiện **không trả lời được** vì chưa có `PaperIndex.status`. Đây là lý do Giai đoạn 3 phải đi trước hoặc song song.

### 13.4. Sáu contract KHÔNG được đập

Bản mới muốn viết lại ruột thế nào cũng được, nhưng phải tôn trọng đủ sáu.

**Contract 1 — Response schema (frontend đang phụ thuộc trực tiếp)**

`SynthesisSessionResponse` (`src/models/synthesis_schemas.py:352-362`):

```python
class SynthesisSessionResponse(BaseModel):
    id: uuid.UUID
    status: str
    research_question: str | None
    qa_warning: str | None
    review_markdown: str | None
    error_message: str | None
    citations: list[SynthesisCitationResponse]
    sections: list[SynthesisSectionResponse]
    evidence_profile: list[SynthesisEvidenceProfileItem]
    dimension_statuses: list[SynthesisDimensionStatusItem]
```

Đã kiểm chứng frontend đọc **đúng** từng field, kể cả cấp lồng `sections[].sentences[].text / sentence_type / claim_ids / citation_ids`.

- Giữ nguyên, **hoặc** version hóa: `/api/v2/...` chạy song song, frontend chuyển khi sẵn sàng.
- Thêm field: chỉ thêm optional, không đổi tên, không đổi kiểu field cũ.
- Contract test **ngay từ commit đầu tiên**, không để cuối.

**Contract 2 — Chuỗi provenance của citation (tài sản quý nhất)**

Đây là thứ phân biệt sản phẩm này với một chatbot tóm tắt:

```
review_markdown
  └─ Citation.review_char_start / review_char_end
       └─ Citation.source_page / source_char_start / source_char_end
            └─ PDFChunk (page_char_start, page_char_end, chunk_index)
                 └─ PageText (full_text, content_hash, parser_name, parser_version)
                      └─ Paper.file_path
```

`ingestion_service.py:71-74` có invariant kiểm tra tại chỗ ghi:

```python
if page_row.full_text[start:end] != chunk.page_content:
    raise ValueError("Cannot persist chunk provenance: raw PageText does not reconstruct chunk content.")
```

Hệ thống **tự chứng minh** offset của chunk tái tạo đúng nội dung từ raw page text. Kiểu đảm bảo này hiếm gặp và không được làm mất.

- Mọi câu trong review phải truy được về `(paper_id, page, char_start, char_end)`, đoạn trích khớp raw text.
- **Không sinh citation từ output của LLM.** ADR fast_v2 đã học bài này: *"Native OpenScholar citations — REJECTED — provenance failures"*, và giữ *"P-165 deterministic finalizer — KEEP — authoritative citations"*. Đây là điểm không thương lượng.

**Contract 3 — Mô hình dữ liệu evidence**

```
SynthesisSession   →  phiên chạy
EvidenceRecord     →  một mẩu bằng chứng, gắn với chunk gốc
EvidenceExtractionAttempt  →  lần thử trích xuất (kể cả thất bại) — audit trail
SynthesisClaim     →  một luận điểm
ClaimEvidenceLink  →  claim ↔ evidence, kèm relation + entailment_status
SynthesisSection   →  một mục trong outline
Citation           →  ánh xạ review ↔ nguồn
RetrievalLog / LLMCallLog / SynthesisMetrics  →  quan sát
```

Bản mới **được** thêm bảng, **không được** bỏ chuỗi neo `Section → Claim → Evidence → Chunk`. Bỏ chuỗi này thì hệ thống không còn kiểm chứng được.

`EvidenceExtractionAttempt` đáng giữ đặc biệt: nó ghi cả những lần trích xuất **thất bại** — dữ liệu để trả lời "vì sao paper này không có evidence" thay vì đoán.

**Contract 4 — Truy cập LLM đi qua router**

```python
from src.services.llm import get_llm
llm = get_llm(task="extract_evidence")
```

Task mới phải có entry riêng trong `TASK_REGISTRY`, không dùng lại capability của task khác cho tiện. Nếu bản mới tự viết cascade thứ 9, toàn bộ công gom 8 bản mất sạch.

**Contract 5 — Chỉ đọc evidence từ index hợp lệ**

- Chỉ đưa vào pipeline paper có `PaperIndex.status == READY`.
- Kiểm embedding identity lock trước khi search. Lệch → `EMBEDDING_INDEX_MISMATCH`, không tự re-embed.
- Không gọi `recover_vectors_for_paper` theo kiểu hiện tại.
- **Read-only đối với vector store.** Việc index thuộc ingestion, không thuộc synthesis. Hiện synthesis đang gián tiếp kích hoạt ghi vector (qua `ensure_paper_ingested` → `add_documents`) và đó là nguồn duplicate ở 2.8.

**Contract 6 — Quan sát được và fail-fast**

- Mọi lệnh gọi LLM ghi `LLMCallLog`; mọi truy vấn retrieval ghi `RetrievalLog`; mỗi phiên ghi `SynthesisMetrics`.
- **Không nhét thông báo lỗi vào trường dữ liệu.** Lỗi → `SynthesisStatus.failed` + `error_message`, không phải một section tên "Lỗi hệ thống".
- Không có `except Exception: pass`. Cần bỏ qua lỗi thì bỏ qua **một loại lỗi cụ thể** và log lý do.

### 13.5. Được đập tự do

Ruột của từng node (prompt, chia batch, cách gọi LLM, cách chấm điểm); số node và thứ tự node; 8 policy module (gộp/tách/viết lại/bỏ); chiến lược retrieval (dimension query, hybrid, rerank, RRF); cách chia claim/section/sentence miễn giữ chuỗi neo; cách xử lý coverage; có dùng LangGraph nữa hay không.

**Contract nằm ở biên, không nằm ở ruột.** Biên này nhỏ hơn nhiều so với 9.348 LOC hiện có — đó là điều làm việc viết lại khả thi.

### 13.6. Chiến lược: strangler, không big-bang

Repo đã có sẵn bằng chứng: `fast_v2` là nỗ lực viết lại 5.889 LOC, chất lượng tốt, tài liệu tốt, nhưng vẫn nằm sau feature flag vì hai tiêu chí thăng cấp chưa đạt. Rủi ro của lần thứ ba là lặp lại đúng vậy — và giờ phải nuôi ba bản.

**Bước 1 — quyết định số phận `fast_v2`.** Ba lựa chọn, phải chọn tường minh và ghi vào ADR:

| Lựa chọn | Khi nào hợp lý |
|---|---|
| **Hoàn thiện fast_v2**, coi là bản viết lại | Nếu vấn đề chủ yếu là kiến trúc/tốc độ, và team giải được hai bài toán ở ADR mục L |
| **Khai tử fast_v2**, xoá khỏi repo, viết lại từ legacy | Nếu fast_v2 sai hướng phương pháp. Phải **trích xuất bài học** trong ADR trước khi xoá — nhất là mục I (4 failure mode của generator) và mục K (bảng frozen/rejected) |
| **Giữ đóng băng**, tập trung chẻ nhỏ legacy | Nếu vấn đề chỉ là code không sửa nổi |

Không chọn thì mặc định rơi vào trường hợp tệ nhất: nuôi song song ba bản.

**Bước 2 — đo trước khi đập.** Cần bộ đánh giá tối thiểu, chạy lặp lại được:

- Corpus cố định (10–20 paper, đã ingest bằng embedding thật, verify `READY`).
- Tập research question cố định.
- Số đo: tỉ lệ câu có citation hợp lệ, tỉ lệ citation trích đúng raw text, số claim không có evidence, độ trễ, số lệnh gọi LLM, chi phí token.

Phần lớn lấy được từ bảng đã có (`LLMCallLog`, `RetrievalLog`, `SynthesisMetrics`, `Citation`). Repo cũng đã có `ragas_eval_service.py` và `rag_eval_harness.py`. Lưu ý chi phí: RAGAS dùng LLM làm giám khảo, mỗi mẫu khoảng 4 lệnh gọi — cần tính vào ngân sách và đi qua router có giới hạn.

**Bước 3 — thay từng node, không thay cả pipeline.** Với mỗi node trong 9 node: định nghĩa input/output là Pydantic model tường minh → viết bản mới → A/B trên corpus cố định → so số → thay thế. Mỗi node một PR.

Ưu điểm: mỗi bước revert được, luôn có hệ thống chạy được, và số đo cho biết node nào thực sự là nguồn của "siêu tệ" — có thể chỉ 2/9 node là vấn đề, lúc đó đập cả hệ thống là lãng phí.

**Nếu vẫn quyết viết mới hoàn toàn:** chạy song song sau feature flag mới (`SYNTHESIS_MODE=v3`), định nghĩa **trước** tiêu chí thăng cấp theo mẫu ADR fast_v2 mục M, và **định ngày khai tử bản cũ ngay lúc bắt đầu**. Không có ngày đó thì repo tích luỹ bản thứ ba thay vì thay thế bản thứ nhất.

### 13.7. Checklist nghiệm thu cho bản synthesis mới

**Contract biên**
- [ ] `SynthesisSessionResponse` giữ nguyên, hoặc có `/v2` song song; frontend không phải sửa gấp
- [ ] Contract test cho response schema, chạy trong CI
- [ ] Mọi câu trong review truy được về `(paper_id, page, char_start, char_end)`; đoạn trích khớp raw `PageText`
- [ ] Citation do tầng deterministic sinh, không lấy từ output LLM
- [ ] Chuỗi `Section → Claim → Evidence → Chunk` còn nguyên

**Lắp vào kế hoạch chuẩn hóa**
- [ ] 0 lệnh gọi LLM nào ngoài `get_llm(task=...)`
- [ ] Mọi task mới có entry trong `TASK_REGISTRY` với capability khai báo
- [ ] Chỉ nhận paper `PaperIndex.status == READY`
- [ ] Read-only với vector store; không embed, không ghi, không tự recover
- [ ] Kiểm embedding identity lock trước khi search

**Không tái phạm**
- [ ] 0 chỗ `except Exception: pass`
- [ ] 0 chỗ nhét thông báo lỗi vào trường dữ liệu
- [ ] Lỗi → `status=failed` + `error_message`, không phải section giả
- [ ] Ghi đủ `LLMCallLog`, `RetrievalLog`, `SynthesisMetrics`
- [ ] Không method nào quá ~80 dòng

**Chứng minh tốt hơn**
- [ ] Có số đo baseline của bản cũ trên corpus cố định
- [ ] Bản mới thắng bản cũ trên ít nhất: tỉ lệ citation hợp lệ, số claim không có evidence, chi phí token/phiên
- [ ] Tiêu chí thăng cấp viết ra **trước** khi code
- [ ] Có ngày khai tử cho bản cũ, ghi trong ADR

---
---

# PHẦN III — THI CÔNG

## 14. Kế hoạch theo giai đoạn

Thứ tự tối ưu theo *rủi ro giảm được trên mỗi đơn vị công sức*, không theo thứ tự kiến trúc.

> **Trạng thái thi công (cập nhật 2026-08-26).** Giai đoạn 0, 1, 2, 3 đã được thực hiện trên nhánh
> `docs/system-contracts-audit-and-plan`. Xem [TRANG_THAI_THI_CONG.md](./TRANG_THAI_THI_CONG.md)
> để biết mục nào đã xong, mục nào cố ý hoãn và vì sao.
> Giai đoạn 4 (LLM Router), 5 (API contract) và 6 (Synthesis) chưa bắt đầu.

### Giai đoạn 0 — Khẩn cấp, bảo mật (độc lập với mọi việc khác)

| Việc | Vị trí |
|---|---|
| Thêm dependency xác thực cho toàn bộ 56 route; bỏ tin `X-User-Id` không xác thực | `src/api/*`, `project_routes.py:64-86` |
| Bảo vệ `/auth/admin/stats` và `/auth/admin/users/{id}` bằng kiểm tra role | `auth_routes.py:170,219` |
| Bỏ seed admin `admin123`/`123`; nếu cần seed thì chỉ khi `APP_ENV=development`, mật khẩu lấy từ env | `main.py:141-165` |
| Bỏ giá trị hardcode của `SECRET_KEY`; thiếu biến thì **dừng khởi động** | `auth_routes.py:28` |
| `/auth/google`: không có token hợp lệ → **401**, bỏ email bịa | `auth_routes.py:241-284` |
| `/health` không trả prefix key; hoặc yêu cầu xác thực | `main.py:195-203` |
| Xoay toàn bộ key đang dùng (Google client ID, SerpAPI, LLM key) vì đã nằm trong repo/log công khai | vận hành |
| Thay `sk-placeho` trên production bằng key thật, hoặc tắt tính năng LLM cho tới khi có key | vận hành |

### Giai đoạn 1 — Chặn thất thoát tiền

| Việc | Vị trí |
|---|---|
| Bỏ nhánh `FakeEmbeddings` + Gemini fallback; khôi phục fail-fast (tham chiếu `5fbc555`) | `vector_store.py:80-95` |
| Sửa docstring cho khớp hành vi thật | `vector_store.py:52-56` |
| Phân loại lại lỗi permanent/transient theo bảng 10.5 | `synthesis_llm_service.py:110-136` |
| Bỏ `sk-placeholder` và `claude-opus-5-thinking` | `synthesis_llm_service.py:96-97` |
| Giảm candidate từ 6 xuống ≤2; bỏ 2 fallback hardcode | `synthesis_llm_service.py:198-297` |
| Thay `random.choice` bằng round-robin xác định + log alias | `config.py:86-95` |
| `add_documents` raise thay vì `return 0` | `vector_store.py:187-189` |

Không cần schema mới, làm được ngay, cắt phần lớn chi phí lãng phí.

### Giai đoạn 2 — Chuẩn hóa môi trường

Toàn bộ mục 12. Sau giai đoạn này, mọi người mới thực sự chạy cùng một hệ thống — điều kiện cần để giai đoạn 3 và 4 kiểm chứng được.

Cần một buổi đồng bộ cả team: ai cũng xóa `.env` cũ, lấy `.env.example` mới, cài lại dependency từ lock, chạy `alembic stamp` + `upgrade`.

### Giai đoạn 3 — Vector Index contract

| Việc |
|---|
| Thêm bảng `VectorIndex` (+ `PaperIndex`) và migration Alembic |
| Viết `embedding_manager.py`; ghi identity vào Chroma collection metadata |
| `verify_collection_lock` — đối chiếu ba chiều DB / Chroma / runtime |
| Sửa `recover_vectors_for_paper` dùng manifest thay vì runtime config |
| Thêm vòng đời `PENDING → INDEXING → READY / FAILED`, đảo thứ tự commit |
| Truyền `ids` tường minh cho Chroma; bỏ nhánh re-add gây duplicate |
| Script/endpoint re-index có versioning (build v2 xong mới switch) |
| Structured error `EMBEDDING_INDEX_MISMATCH` + UI có nút Re-index |
| PDF parse lỗi → `FAILED`, không âm thầm rơi về index abstract |

### Giai đoạn 4 — LLM Runtime contract

Chia nhỏ để làm độc lập, mỗi bước tự nó có giá trị:

**4a. Registry (chưa đổi hành vi, an toàn merge sớm)**

| Việc |
|---|
| Tạo `registry.py`, điền 16 model đang dùng cùng capability đã kiểm chứng |
| Tạo `capability.py` với 14 task đã liệt kê ở 10.4 |
| Validate lúc khởi động: model trong `.env` phải có trong registry, nếu không thì dừng |
| Kiểm tra CI chặn tên model literal xuất hiện ngoài `registry.py` |

**4b. Router**

| Việc |
|---|
| `credentials.py`: đọc key theo provider, round-robin, đánh dấu key ngưng |
| `errors.py` theo bảng 10.5 |
| `router.py`: `get_llm(task=...)` với capability gate |
| `observability.py`, bổ sung cột cho `LLMCallLog` |
| Ngân sách LLM per-session |

**4c. Di dời call site (từng file một, review được)**

| Thứ tự | File | Ghi chú |
|---|---|---|
| 1 | `synthesis_llm_service.py` | quan trọng nhất, giảm candidate 6 → ≤2 |
| 2 | `rag_service.py:251-341` | cascade lớn thứ hai |
| 3 | `deps_provider.py:70-89` | |
| 4 | `criteria_generator.py:74-118` | kèm sửa lỗi trả thông báo lỗi trong trường dữ liệu (dòng 139-150) |
| 5 | `gap_finder.py:198-242` | |
| 6 | `scope_optimizer.py:77-121` | |
| 7 | `project_routes.py:368-420` | |

**4d. Dọn `config.py`** — chỉ làm **sau khi** mọi call site đã dùng router:

| Việc |
|---|
| Bỏ `effective_openai_api_key` (gộp 4 provider) |
| Bỏ suy ra base URL từ prefix key |
| Bỏ viết lại tên model từ prefix key |
| Tách biến credential/model theo từng provider |
| Bỏ đánh chỉ số key theo vị trí trong các agent SLR-swarm |

**4e. Test giữ hành vi** — chạy trên **mọi** nhánh trong CI:

| Test |
|---|
| Không có key nào → `get_llm` raise, **0 lệnh gọi mạng** |
| 401 → không retry cùng key, chuyển key kế |
| 404 → dừng ngay, không thử candidate khác |
| 429 → key bị đánh dấu ngưng, không thử lại trong cùng request |
| Model không có trong registry → app **không khởi động** |
| Task yêu cầu `json_schema`, không provider nào hỗ trợ → raise `NoCapableProviderError`, không hạ chuẩn |
| Đổi key trong cùng provider+model → không phát sinh thay đổi nào ở vector index |

Test cuối khóa chặt ranh giới giữa "đổi credential" (an toàn) và "đổi model" (phải migration).

### Giai đoạn 5 — API contract & dọn nợ

| Việc |
|---|
| Contract test cho các endpoint chính |
| Zod validation tại client HTTP thống nhất (phương án A ở 11.4) |
| Gộp `fetch` trực tiếp về một client duy nhất; bỏ fallback mixed-content |
| Rà 55 vị trí `except Exception: pass` theo tiêu chí mục 8 |
| Bỏ `scopus_matcher` đoán quartile; bỏ seed `sourcerecord_id` bịa trong `main.py` |
| Xóa hàm trùng tên trong `scholar_api.py` |
| Dùng `settings.cors_origins` thay cho `allow_origins=["*"]` |
| Xác nhận nội dung gửi tới `AI_LOG_SERVER` |

### Giai đoạn 6 — Synthesis

Toàn bộ mục 13. Phụ thuộc thứ tự:

```
Giai đoạn 0 (bảo mật)              ─┐
Giai đoạn 1 (chặn đốt tiền)         ├─ làm trước, độc lập, không đụng synthesis
Giai đoạn 2 (chuẩn hóa môi trường)  ─┘
        │
        ▼
Giai đoạn 3 (Vector Index contract)
        │   ← BẮT BUỘC trước khi đánh giá chất lượng synthesis
        │     (không có PaperIndex.status thì không biết
        │      evidence đầu vào có sạch không)
        ▼
Giai đoạn 4 (LLM Router)
        │   ← nên xong trước, để bản mới viết thẳng trên router
        ▼
Giai đoạn 6 (Xây lại synthesis)
```

Việc chẻ nhỏ 6 method khổng lồ (13.2) có thể làm **song song** với các giai đoạn trên — không đổi hành vi, chỉ đổi cấu trúc, rủi ro thấp, giao cho người khác làm độc lập được.

---

## 15. Định nghĩa hoàn thành

Coi là xong khi tất cả những điều sau đúng:

**Môi trường**
- Hai người khác máy, cùng commit, cùng `.env` → cùng database, cùng vector store, cùng bộ thư viện.
- Thiếu cấu hình bắt buộc → app **không khởi động**, kèm thông báo nêu đúng biến thiếu.

**Tiền**
- Không có key hợp lệ → **0** lệnh gọi API được phát ra.
- Lỗi permanent (401/404/400) → dừng ngay, không retry.
- Mỗi lệnh gọi LLM đều truy được: task nào, provider nào, key alias nào, hết bao nhiêu token.

**Dữ liệu**
- Không tồn tại đường nào trong production ghi vector không phải do model đã khai báo sinh ra.
- Mọi paper trong RAG đều có `PaperIndex.status == READY`.
- Đổi model embedding chỉ đi qua re-index có version, không bao giờ qua fallback.
- Không trường dữ liệu nào chứa thông báo lỗi.

**Contract**
- Đổi schema response mà không cập nhật consumer → **CI đỏ**, không phải "deploy xong thấy UI trắng".
- Test khẳng định hành vi fail-fast chạy trên mọi nhánh, và commit đảo ngược chúng bị CI chặn.

Tiêu chí cuối là quan trọng nhất. Vấn đề gốc của repo không phải team không biết sửa — bản vá `5fbc555` cho thấy team đã sửa đúng một lần, kèm test. Vấn đề là **không có cơ chế nào giữ được bản vá đó**. Mọi thứ trong tài liệu này chỉ có giá trị nếu có cơ chế ngăn nó bị đảo ngược một cách vô tình.

---

## Phụ lục — Kết luận

Vấn đề của repo không phải *"fallback provider hơi tùm lum"*, cũng không phải *"nhiều người dùng nhiều API key khác nhau"*. Việc mỗi người dùng key riêng là nhu cầu hợp lý và hoàn toàn giải quyết được.

Vấn đề là: **repo thiếu contract và invariant rõ ràng ở các boundary có state, nên rất nhiều lỗi bị chuyển hóa thành "thành công giả"** — pipeline vẫn chạy, nhưng dữ liệu hoặc output không còn mang ý nghĩa mà tầng sau đang giả định là nó có.

Ba boundary bị vi phạm, cùng một cơ chế:

```
1. Identity contract (embedding)
   config nói OpenAI → runtime fallback Gemini/Fake → collection vẫn tên "openai"

2. Persistence contract (vector recovery)
   index lịch sử dùng model A → runtime hiện tại là model B
   → auto-recovery lấy B để sửa dữ liệu của A

3. Environment contract (dev setup)
   .env nói PostgreSQL + Chroma server
   → máy không có Docker âm thầm chạy SQLite + Chroma embedded
```

Hướng xử lý thống nhất cho cả ba tầng:

```
explicit identity  +  explicit metadata  +  validation tại boundary
+  structured error  +  contract test  +  không silent fallback
```
