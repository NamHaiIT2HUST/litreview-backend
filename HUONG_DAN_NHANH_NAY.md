# Nhánh `docs/system-contracts-audit-and-plan` — Hướng dẫn cài đặt & giải thích

Nhánh này sửa nhóm lỗi khiến team gặp cảnh *"mỗi người làm một tính năng, ghép lại thì lỗi;
kéo code về máy chỉ chạy được phần mình; gọi API vẫn trừ tiền nhưng không ra kết quả"*.

**Đọc mục [Cài đặt](#cài-đặt) trước khi chạy.** Nhánh này **cố ý** làm app không khởi động
được nếu cấu hình sai, thay vì chạy tiếp trong trạng thái sai — nên nếu bỏ qua các bước
dưới, app sẽ báo lỗi ngay lúc start. Đó là chủ đích.

---

## Mục lục

- [Tóm tắt: nhánh này sửa gì](#tóm-tắt-nhánh-này-sửa-gì)
- [Cần chuẩn bị gì](#cần-chuẩn-bị-gì)
- [Cài đặt](#cài-đặt)
- [Chạy](#chạy)
- [Nếu app không khởi động](#nếu-app-không-khởi-động)
- [Những thay đổi ảnh hưởng tới cách làm việc hằng ngày](#những-thay-đổi-ảnh-hưởng-tới-cách-làm-việc-hằng-ngày)
- [Cần kiểm thử những gì](#cần-kiểm-thử-những-gì)
- [Việc vận hành cần làm](#việc-vận-hành-cần-làm)
- [Tài liệu chi tiết](#tài-liệu-chi-tiết)

---

## Tóm tắt: nhánh này sửa gì

Chẩn đoán chung: **hệ thống thiếu contract rõ ràng ở những ranh giới có state, nên rất nhiều
lỗi bị biến thành "thành công giả"** — pipeline vẫn chạy, HTTP vẫn 200, DB vẫn có dữ liệu,
log vẫn báo thành công, nhưng dữ liệu hoặc output không còn mang ý nghĩa mà tầng sau đang
giả định là nó có.

| Nhóm | Trước | Sau |
|---|---|---|
| **Bảo mật** | 56 route API, 0 route có xác thực. `/auth/admin/*` mở công khai. `SECRET_KEY` hardcode trong repo. Frontend đăng nhập bất kỳ ai gõ bất kỳ gì, không kiểm mật khẩu | Có `get_current_user` / `require_admin`. Admin route được bảo vệ. Thiếu `SECRET_KEY` thì không khởi động. Đăng nhập phải qua backend |
| **Tiền** | Thiếu key OpenAI → âm thầm dùng vector ngẫu nhiên. Key sai → tới 24 lệnh gọi tính phí cho một bước | Thiếu key → báo lỗi rõ. Key sai → 1 lệnh gọi rồi chuyển key/provider |
| **Môi trường** | 56 dependency không pin. Postgres lỗi → âm thầm dùng SQLite. Worktree âm thầm nạp `.env` của thư mục cha | `requirements.lock` 188 package. DB lỗi → dừng, báo rõ. `.env` đọc theo project root |
| **Dữ liệu** | Đổi embedding model ghi đè lên index cũ. PDF parse lỗi → âm thầm index abstract. Chunk nhân bản mỗi lần chạy | Index khóa theo (provider, model, dimension). Parse lỗi → báo lỗi. Chunk có id cố định |
| **LLM** | 16 tên model rải 8 file, 8 bản cascade khác nhau | 1 router, capability gate, ưu tiên provider theo `.env` từng người |
| **Toàn vẹn** | Quartile Scopus bịa theo số trích dẫn. ID Scopus bịa. Lỗi trả về trong trường dữ liệu | Không tìm thấy → `undetermined`. ID có tiền tố `seed:`. Lỗi trả về là lỗi |

**Test:** 9 failed / 602 passed → **1 failed / 668 passed**. Lỗi còn lại (`test_agent_basic_flow`)
đã có từ trước nhánh này.

---

## Cần chuẩn bị gì

| Thứ | Phiên bản | Bắt buộc? | Ghi chú |
|---|---|---|---|
| **Python** | 3.11 | Có | Khớp CI và Dockerfile. 3.12 vẫn chạy nhưng lockfile compile trên 3.11 |
| **Node.js** | 20 trở lên | Có | Cho frontend |
| **Git** | bất kỳ | Có | |
| **Docker Desktop** | mới nhất | Nên có | Cho PostgreSQL + Redis + Chroma. Không có vẫn chạy được bằng SQLite, xem [Cách B](#cách-b--không-dùng-docker-nhẹ-hơn-đủ-để-thử-tính-năng) |
| **API key LLM** | — | Nên có | Gemini / OpenAI / Groq. Không có thì các tính năng AI sẽ báo lỗi rõ ràng thay vì chạy sai |

Kiểm tra nhanh:

```bash
python --version
node --version
docker --version
```

---

## Cài đặt

### 0. Lấy code

```bash
git fetch origin
git checkout docs/system-contracts-audit-and-plan
```

### 1. Python

Cần **Python 3.11** (khớp CI và Dockerfile).

```bash
python -m venv .venv
```

```bash
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

Cài từ **lockfile**, không phải `requirements.txt`:

```bash
pip install -r requirements.lock
```

> `requirements.txt` chỉ ghi khoảng phiên bản (`>=`) nên hai người cài cách nhau vài tuần
> nhận hai bộ thư viện khác nhau từ cùng một commit. Đây là nguyên nhân nhiều khả năng nhất
> của *"code y hệt mà máy tôi chạy được, máy bạn không"*. `requirements.lock` ghim đúng 188
> package.

### 2. Tạo `.env`

```bash
cp .env.example .env
```

**Bắt buộc:** sinh `SECRET_KEY`. App từ chối khởi động nếu thiếu.

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Dán vào `.env`:

```env
SECRET_KEY=<chuỗi vừa sinh>
```

> Trước đây có giá trị dự phòng hardcode ngay trong `auth_routes.py`. Ai đọc được repo đều ký
> được token hợp lệ. Giờ không có giá trị mặc định nào.

**Quan trọng nếu anh/chị đã có `.env` cũ:** hãy lấy lại từ `.env.example` mới. File cũ đặt
`SYNTHESIS_MODE=fast_v2_experimental` và `FAST_V2_RERANKER=cross_encoder`, trái với default an
toàn mà `config.py` ghi rõ — nghĩa là ai copy `.env.example` cũ đều đang chạy pipeline thử
nghiệm chưa kiểm chứng về grounding, và tải model reranker về máy, mà không biết.

### 3. Chọn database — không còn tự đoán

Không còn fallback âm thầm sang SQLite. Phải chọn tường minh một trong hai cách dưới.

> **Vì sao bước này quan trọng:** trước đây `.env.example` trỏ vào Postgres cổng 5434. Ai bật
> Docker thì dùng Postgres, ai không bật thì **âm thầm** rơi về SQLite, chỉ báo bằng một dòng
> `print()` lẫn trong log khởi động. Cùng commit, cùng `.env`, **hai database khác nhau** — và
> không có gì trong `/health` cho biết đang dùng cái nào. Dữ liệu ghi trong phiên đó mất khi
> restart. Đây là một trong những lý do chính khiến "tính năng của người kia không chạy trên
> máy tôi".

---

#### Cách A — Dùng Docker (khuyến nghị, giống môi trường thật nhất)

**Docker là gì và vì sao cần:** dự án này cần 3 dịch vụ nền chạy song song với app —
PostgreSQL (database), Redis (hàng đợi tác vụ nền), và Chroma (kho vector cho tìm kiếm ngữ
nghĩa). Cài từng cái bằng tay trên Windows/macOS rất mất công và mỗi máy một phiên bản khác
nhau. Docker chạy cả 3 trong container, cùng phiên bản trên mọi máy.

**Bước 1 — Cài Docker Desktop**

- Windows / macOS: tải tại <https://www.docker.com/products/docker-desktop/>
- Linux: cài `docker` và `docker compose` theo hướng dẫn distro

Windows lưu ý: Docker Desktop cần **WSL2**. Trình cài đặt thường tự bật; nếu báo lỗi, mở
PowerShell quyền Administrator và chạy `wsl --install`, sau đó khởi động lại máy.

**Bước 2 — Mở Docker Desktop và đợi nó chạy xong**

Docker Desktop phải đang chạy thì lệnh `docker` mới hoạt động. Kiểm tra:

```bash
docker --version
```

Ra số phiên bản là được. Nếu báo *"Cannot connect to the Docker daemon"* nghĩa là Docker
Desktop chưa khởi động xong — mở app lên và đợi biểu tượng cá voi báo *Running*.

**Bước 3 — Bật các dịch vụ nền**

Chạy ở thư mục gốc dự án:

```bash
docker compose up -d db redis chroma
```

`-d` nghĩa là chạy nền, không chiếm terminal.

Lần đầu sẽ tải image về (vài trăm MB, mất vài phút). Những lần sau chỉ vài giây.

**Bước 4 — Kiểm tra cả 3 đã chạy**

```bash
docker compose ps
```

Phải thấy `litreview-db`, `litreview-redis`, `litreview-chroma` ở trạng thái `Up`
(riêng `db` và `redis` sẽ hiện thêm `healthy`).

**Bước 5 — Khai báo trong `.env`**

Ba dịch vụ này chạy trong container nhưng được "mở cổng" ra máy thật:

| Dịch vụ | Cổng trên máy bạn | Dùng để làm gì |
|---|---|---|
| PostgreSQL | `5434` | Database chính |
| Redis | `6379` | Hàng đợi cho synthesis chạy nền |
| Chroma | `8001` | Kho vector cho tìm kiếm ngữ nghĩa |

Trong `.env`:

```env
DATABASE_URL=postgresql://postgres:password@localhost:5434/litreview
REDIS_URL=redis://localhost:6379/0

# Bật Chroma dạng server. Để trống sẽ dùng Chroma nhúng (file cục bộ),
# chỉ an toàn khi chạy đúng một tiến trình.
CHROMA_HOST=localhost
CHROMA_PORT=8001
```

> Lưu ý cổng: bên trong mạng Docker, Postgres là `5432` và Chroma là `8000`. Từ máy thật thì
> lần lượt là `5434` và `8001`. Nếu chạy backend **bên trong** Docker (xem bên dưới),
> `docker-compose.yml` tự đặt đúng giá trị nội bộ — không cần sửa gì.

**Các lệnh Docker hay dùng**

```bash
docker compose ps                  # xem dịch vụ nào đang chạy
docker compose logs -f db          # xem log realtime (Ctrl+C để thoát)
docker compose stop                # tạm dừng, GIỮ nguyên dữ liệu
docker compose start               # chạy lại
docker compose down                # xoá container, VẪN GIỮ dữ liệu (nằm trong volume)
docker compose down -v             # xoá luôn dữ liệu — dùng khi muốn làm sạch từ đầu
```

`down -v` xoá sạch database và vector store. Chỉ dùng khi thật sự muốn bắt đầu lại.

**Chạy luôn cả backend trong Docker (tuỳ chọn)**

Nếu không muốn cài Python trên máy:

```bash
docker compose up -d
```

Lệnh này chạy tất cả, gồm cả `backend` ở cổng `8000`. Lần đầu sẽ build image (khá lâu, 5–15
phút). Frontend vẫn chạy ngoài bằng `npm run dev`.

Muốn chạy thêm worker xử lý synthesis nền:

```bash
docker compose --profile worker up -d
```

`worker` nằm trong profile riêng nên mặc định không chạy — phải gọi tên profile mới bật.

---

#### Cách B — Không dùng Docker (nhẹ hơn, đủ để thử tính năng)

Nếu chỉ muốn xem app chạy và không cần Postgres/Redis, khai báo tường minh dùng SQLite:

```env
DATABASE_URL=sqlite:///./data/app.db
CHROMA_HOST=
```

`CHROMA_HOST` để trống nghĩa là dùng Chroma nhúng — lưu vào thư mục `./data/chroma` trên máy.

Giới hạn của cách này:

- Chroma nhúng **chỉ an toàn với một tiến trình**. Nếu chạy thêm Celery worker, API và worker
  sẽ có hai kho vector riêng biệt, không thấy nhau. App sẽ ghi log cảnh báo khi ở chế độ này.
- Synthesis chạy nền (qua Redis/Celery) sẽ không dùng được.
- SQLite không có UUID/JSONB thật như Postgres, nên vài hành vi sẽ khác môi trường production.

Đủ để thử tính năng, nhưng khi nghi ngờ lỗi thì nên kiểm chứng lại bằng Cách A.

### 4. LLM provider

Đặt key cho provider định dùng, và thứ tự ưu tiên:

```env
LLM_PROVIDER_PRIORITY=gemini,openai,groq

GEMINI_API_KEY=AIza...
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...

GEMINI_MODEL=gemini-2.0-flash
OPENAI_MODEL=gpt-4o-mini
```

`LLM_PROVIDER_PRIORITY` nằm trong `.env` **local của từng người**, nên mỗi người ưu tiên key
mình có mà không đụng file chung và không tạo conflict khi merge.

Nhiều key cho một provider (bí danh để log truy vết được, không in key ra):

```env
GEMINI_API_KEYS=lien:AIza...,huyen:AIza...,team:AIza...
```

Key báo hết quota bị ngưng tạm; key bị provider từ chối bị vô hiệu trong phiên chạy.

### 5. Embedding — khác LLM, cần cẩn thận

```env
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
```

Không có key OpenAI thì dùng model local (tự tải lần đầu):

```env
EMBEDDING_PROVIDER=local
LOCAL_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

> **Ranh giới quan trọng nhất của nhánh này:** LLM đổi thoải mái; embedding thì không.
>
> Embedding model định nghĩa *hệ tọa độ* của toàn bộ vector đã lưu. Vector do model A tạo ra
> không so sánh được với vector do model B tạo ra — kể cả cùng số chiều. Kết quả trả về trông
> hoàn toàn bình thường và **không có nghĩa gì**. Vì vậy embedding được quản như *schema của
> database*, không phải như lựa chọn nhà cung cấp.
>
> Hệ quả thực tế:
> - **Đổi API key trong cùng provider + model: an toàn, không cần làm gì.** Identity của index
>   là (provider, model, dimension), không gồm key.
> - **Đổi `EMBEDDING_PROVIDER` hoặc `EMBEDDING_MODEL`: phải re-index.** Đây là migration.

### 6. Frontend

```bash
cd frontend
npm ci
cp .env.example .env.local
```

`npm ci` (không phải `npm install`) để cài đúng lockfile.

`frontend/.env.example` là file mới. Trước đây `VITE_API_BASE` được code dùng nhưng không
document ở đâu, nên không ai set — và một địa chỉ backend hardcode trong `apiConfig.js` quyết
định thay. Giá trị đó **khác nhau theo từng nhánh** (`main` trỏ EC2, `develop` trỏ Railway đã bị
bỏ), nên hai người ở hai nhánh đang đọc/ghi vào hai backend khác nhau mà không biết.

Chạy local thì để nguyên mặc định:

```env
VITE_API_BASE=http://localhost:8000/api/v1
```

### 7. Tài khoản để đăng nhập thử

Tài khoản `admin123/123` **không còn được tạo tự động** (trước đây nó được seed mỗi lần khởi
động ở **mọi** môi trường, kể cả production).

Cách nhanh nhất để vào thử — 2 profile nghiên cứu viên bấm phát vào luôn:

```env
APP_ENV=development
SEED_DEMO_ACCOUNTS=true
SEED_DEMO_PASSWORD=<mật khẩu tự đặt>
```

Hai profile sẽ hiện trên màn hình đăng nhập. Đây là **tài khoản thật trong DB**: bấm vào chạy
`POST /auth/login` bình thường và nhận token thật. Ngoài `development` thì endpoint trả danh
sách rỗng nên picker không hiện.

Hoặc tự tạo tài khoản admin:

```env
SEED_DEFAULT_ADMIN=true
SEED_ADMIN_USERNAME=admin
SEED_ADMIN_PASSWORD=<mật khẩu tự đặt>
```

Hoặc đăng ký qua UI như người dùng bình thường.

---

## Chạy

Cần **hai terminal** chạy song song (ba nếu dùng Docker cho dịch vụ nền).

**Terminal 1 — dịch vụ nền** (bỏ qua nếu dùng Cách B):

```bash
docker compose up -d db redis chroma
```

Chạy nền nên terminal này rảnh lại ngay.

**Terminal 2 — backend:**

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Đợi tới khi thấy `Background tasks scheduled. Server ready.`

**Terminal 3 — frontend:**

```bash
cd frontend && npm run dev
```

Mở <http://localhost:5173>.

Kiểm tra backend sống:

```bash
curl http://localhost:8000/health
```

Phải ra `{"status":"ok","env":"development","version":"1.0.5"}`.

> Không còn trường `openai_key_prefix` / `gemini_key_prefix` như trước. Endpoint này công khai,
> không yêu cầu xác thực, nên nó từng công bố 10 ký tự đầu của API key ra Internet — cũng chính
> là cách phát hiện production đang chạy bằng key giả `sk-placeho`.

### Nếu đã có dữ liệu vector cũ

Tên collection Chroma đổi từ `litreview_papers_{provider}_v3` sang
`index_v1_{provider}_{model}_{dimension}`, nên **vector cũ sẽ không được tìm thấy**:

```bash
python -m scripts.reindex_vectors --plan
python -m scripts.reindex_vectors --build
```

> Đây là chủ đích. Tên cũ chỉ chứa tên provider lấy từ config, nên khi code rơi vào backend
> khác thì tên collection vẫn khai là provider đã cấu hình — tên nói dối về nội dung bên trong.
> Tên mới mô tả đúng thứ nằm trong đó.

Script dựng index mới **song song** với index đang phục vụ, xong mới chuyển
(`--promote`), và chỉ xóa index cũ khi được yêu cầu (`--drop`). Không bao giờ xóa trước rồi
build sau.

---

## Nếu app không khởi động

Nhánh này thay im lặng bằng lỗi rõ ràng. Các lỗi hay gặp:

| Thông báo | Nghĩa là | Sửa |
|---|---|---|
| `SECRET_KEY is not set` | Chưa sinh khóa ký token | Bước 2 phần Cài đặt |
| `Could not connect to the configured database` | DB trong `DATABASE_URL` không kết nối được | `docker compose up -d db`, hoặc chuyển sang SQLite tường minh |
| `EMBEDDING_PROVIDER=openai requires OPENAI_EMBEDDING_API_KEY or OPENAI_API_KEY` | Thiếu key embedding | Đặt key, hoặc `EMBEDDING_PROVIDER=local` |
| `Unknown embedding model ... for provider ...` | Provider và model không khớp nhau | Ví dụ đặt `EMBEDDING_PROVIDER=gemini` nhưng để nguyên `EMBEDDING_MODEL=text-embedding-3-small` |
| `SEED_DEFAULT_ADMIN is only allowed when APP_ENV=development` | Bật seed ngoài môi trường dev | Tắt seed, hoặc đặt `APP_ENV=development` |
| `No configured LLM provider can serve task ...` | Không provider nào vừa có key vừa đủ năng lực | Thông báo liệt kê từng provider và lý do bị loại |

### Lỗi Docker hay gặp

| Thông báo | Nghĩa là | Sửa |
|---|---|---|
| `Cannot connect to the Docker daemon` | Docker Desktop chưa chạy | Mở Docker Desktop, đợi biểu tượng cá voi báo *Running* |
| `port is already allocated` / `bind: address already in use` | Cổng đã bị chương trình khác chiếm | Xem cổng nào trong thông báo. Nếu đã có PostgreSQL cài sẵn trên máy chiếm 5434, tắt nó hoặc sửa cổng trong `docker-compose.yml` |
| `docker: 'compose' is not a docker command` | Docker quá cũ | Cập nhật Docker Desktop. Bản cũ dùng `docker-compose` (có gạch nối) |
| Backend báo `Could not connect to the configured database` dù container đang chạy | Container chưa sẵn sàng, hoặc cổng trong `.env` sai | Chạy `docker compose ps` xem `db` đã `healthy` chưa; kiểm tra `.env` ghi `localhost:5434` |
| Container `db` liên tục restart | Volume dữ liệu cũ hỏng | `docker compose down -v` rồi `docker compose up -d db` (xoá sạch dữ liệu) |
| Trên Windows, Docker Desktop không khởi động | Thiếu WSL2 | PowerShell quyền Administrator: `wsl --install`, khởi động lại máy |

Xem log để biết chi tiết:

```bash
docker compose logs db
docker compose logs chroma
```

Lỗi khi gọi API (HTTP, không phải lúc khởi động):

| Mã | `error_code` | Nghĩa |
|---|---|---|
| 409 | `EMBEDDING_INDEX_MISMATCH` | Index được tạo bằng model khác model đang cấu hình. Cần re-index |
| 503 | `EMBEDDING_NOT_CONFIGURED` | Cấu hình embedding sai |
| 503 | `NO_CAPABLE_LLM_PROVIDER` | Không provider nào phục vụ được task này |
| 429 | `LLM_BUDGET_EXCEEDED` | Một phiên vượt ngưỡng số lệnh gọi LLM |
| 422 | `PDF_INGESTION_FAILED` | PDF không đọc được, **chưa** được ingest |
| 401 | — | Thiếu hoặc sai token |

---

## Những thay đổi ảnh hưởng tới cách làm việc hằng ngày

### Đăng nhập

Mọi request tới API đều tự động gắn token từ `localStorage`. Token cũ (ký bằng `SECRET_KEY`
hardcode) không còn hợp lệ — cần **đăng nhập lại**.

Đã bỏ ba đường đăng nhập giả trong frontend, trong đó có một nhánh tên
*"Seamless Academic Session Creation"* đăng nhập **bất kỳ ai gõ bất kỳ định danh nào, không
kiểm mật khẩu**, và lưu chuỗi `'local_session_token'` làm access token.

### Đổi provider/key LLM

Sửa `.env`, không sửa code:

```env
LLM_PROVIDER_PRIORITY=openai,gemini    # đổi thứ tự ưu tiên
OPENAI_API_KEY=sk-...                  # đổi key
```

Không cần re-index, không cần đụng file chung.

Log mỗi lần chọn provider tự giải thích:

```
llm.select task=extract_evidence needs=json_schema ctx>=32000
  skipped=groq(no credential configured (GROQ_API_KEY is unset))
  selected=gemini:gemini-2.0-flash key=lien
```

### Thêm nhà cung cấp LLM mới

Một entry trong `src/services/llm/registry.py` + một biến credential. **Không sửa file nào
khác** — đó là tiêu chí nghiệm thu của thiết kế này.

### Lỗi giờ nổi lên thành lỗi

Trước đây nhiều lỗi được trả về **dưới dạng dữ liệu**: khi hết quota, hàm sinh tiêu chí trả
`criteria_include=["⚠️ Hệ thống đang tạm thời hết hạn mức AI..."]` — chuỗi đó đi vào đúng ô
dành cho tiêu chí lựa chọn nghiên cứu, HTTP 200, và có thể được lưu vào DB rồi xuất ra báo cáo
PRISMA. Giờ trả HTTP 503 kèm `error_code`.

### Trạng thái Scopus

Tạp chí không có trong bảng nguồn Scopus giờ hiển thị **"chưa xác định"** thay vì Q1/Q2.

Trước đây code đoán: nếu tên tạp chí chứa tên nhà xuất bản quen thuộc, hoặc bài có DOI, hoặc có
trích dẫn, thì gán `indexed` và bịa quartile theo số trích dẫn — kèm comment *"to look
professional"*. Docstring của **chính module đó** đã ghi rõ quartile phải luôn là None vì file
nguồn Scopus không hề có cột quartile.

Danh sách paper vẫn hiện đầy đủ (bộ lọc đã nhận cả `undetermined`), chỉ là nhãn trạng thái nói
thật.

---

## Cần kiểm thử những gì

Đây là phần cần nhiều người thử, vì thay đổi chạm nhiều luồng:

- [ ] Đăng ký tài khoản mới → đăng nhập → tạo project
- [ ] Đăng nhập bằng 2 profile demo (nếu bật `SEED_DEMO_ACCOUNTS`)
- [ ] Đăng nhập Google (cần `GOOGLE_CLIENT_ID` ở backend và `VITE_GOOGLE_CLIENT_ID` khớp)
- [ ] Gợi ý keyword bằng AI
- [ ] Gợi ý tiêu chí Inclusion/Exclusion bằng AI
- [ ] Phân tích phạm vi nghiên cứu (scope)
- [ ] Tìm kiếm paper (SerpAPI / Semantic Scholar / OpenAlex / CrossRef)
- [ ] Kiểm tra Scopus — xác nhận hiện "chưa xác định" thay vì Q1/Q2 bịa
- [ ] Upload PDF → ingest → thấy paper trong workspace
- [ ] Upload một PDF scan (không có text) → phải báo lỗi rõ, **không** âm thầm nhận
- [ ] Chat RAG trên tài liệu đã upload
- [ ] Synthesis (chưa động tới ở nhánh này, cần xác nhận không bị vỡ)
- [ ] Export
- [ ] Trang admin (cần tài khoản role admin)

Báo lỗi kèm: thông báo trên UI, `error_code` nếu có, và log backend.

---

## Việc vận hành cần làm

**Xoay toàn bộ key.** Những thứ sau nằm trong lịch sử git công khai và phải coi như đã lộ —
xóa khỏi code không đủ, lịch sử vẫn còn:

- `SECRET_KEY` cũ: `SUPER_SECRET_KEY_LITREVIEW_AI20K_AGENT_TOKEN_SECRET_KEY_2026`
- `GOOGLE_CLIENT_ID` hardcode trong `auth_routes.py`
- Mọi API key từng xuất hiện trong log hoặc trong phản hồi `/health`

**Production đang chạy với key giả.** `/health` của EC2 trả `"openai_key_prefix":"sk-placeho"`.
Sau nhánh này trạng thái đó sẽ báo lỗi cấu hình rõ ràng thay vì âm thầm bắn request thất bại.
Cần đặt key thật, hoặc tắt tính năng LLM cho tới khi có.

**Đổi mật khẩu tài khoản `admin123` đang tồn tại trong DB.** Nhánh này ngừng *tạo* tài khoản đó
nhưng không xóa tài khoản đã có.

**IP EC2 là IP động**, đã đổi hai lần trong một ngày (`18.143.200.110` → `13.212.121.28`). Nên
gắn Elastic IP hoặc dùng DNS name. Xem
[docs/architecture/DEPLOY_BACKEND_ORIGIN.md](docs/architecture/DEPLOY_BACKEND_ORIGIN.md).

---

## Còn lại — chưa làm, đã ghi rõ lý do

1. **50/56 route API vẫn chưa có xác thực.** Mới bảo vệ `/projects` và `/auth/admin/*`. Hạ tầng
   đã sẵn (`Depends(get_current_user)`), nhưng gắn cả 56 route cùng lúc sẽ vỡ những luồng đang
   dựa vào "Default Project" không có chủ. **Đây là hở lớn nhất còn lại.**
2. **Alembic đang hỏng.** `alembic upgrade head` fail trên SQLite vì revision đầu tạo cột
   `ARRAY` trong khi model đã chuyển JSON. Vẫn dùng `create_all()`; cần sinh lại baseline
   revision trước.
3. **894 lỗi ruff có sẵn** làm CI đỏ (tích tụ vì `ruff>=0.8.0` không pin). 728 lỗi tự sửa được,
   nhưng nên để một commit riêng để review được.
4. **Contract test / Zod validation** giữa backend và frontend chưa làm.
5. **Synthesis** chưa động tới. Xem mục 13 của `SYSTEM_CONTRACTS.md` trước khi định viết lại —
   repo đã có sẵn một bản viết lại (`fast_v2`, 5.889 LOC) đang kẹt ở hai bài toán nghiên cứu.

---

## Tài liệu chi tiết

| File | Nội dung |
|---|---|
| [docs/architecture/SYSTEM_CONTRACTS.md](docs/architecture/SYSTEM_CONTRACTS.md) | Audit đầy đủ (bằng chứng kèm `file:line`), thiết kế 3 tầng contract, kế hoạch 7 giai đoạn. ~1.900 dòng |
| [docs/architecture/TRANG_THAI_THI_CONG.md](docs/architecture/TRANG_THAI_THI_CONG.md) | Đã làm gì / hoãn gì / vì sao, theo từng giai đoạn |
| [docs/architecture/DEPLOY_BACKEND_ORIGIN.md](docs/architecture/DEPLOY_BACKEND_ORIGIN.md) | Địa chỉ backend nằm ở đâu, đổi thế nào |
| [docs/architecture/FAST_SYNTHESIS_V2.md](docs/architecture/FAST_SYNTHESIS_V2.md) | ADR có sẵn của bản synthesis thử nghiệm |

### Các commit trên nhánh

| Commit | Nội dung |
|---|---|
| `d9bff4b` | Tài liệu audit + kế hoạch chuẩn hóa |
| `3f9bc57` | Giai đoạn 0+1 — xác thực API, chặn fallback câm |
| `83fbde7` | Giai đoạn 2 — pin dependency, cấu hình tái lập được |
| `713f069` | Giai đoạn 3 — embedding model như schema của index |
| `255fc75` | Khôi phục tài khoản demo thành tài khoản thật |
| `3285c9d` | Giai đoạn 4+5 — LLM router, toàn vẹn dữ liệu |

Mỗi commit message giải thích *vì sao*, không chỉ *cái gì* — đọc `git log` sẽ hiểu bối cảnh của
từng thay đổi.

---

## Nguyên tắc xuyên suốt

Nếu chỉ nhớ một điều từ nhánh này:

> **Không được "graceful fallback" nếu fallback làm thay đổi ý nghĩa của dữ liệu, hoặc khiến hệ
> thống trả ra output trông đúng nhưng thực chất không đáng tin.**

`FakeEmbeddings` chỉ là biểu hiện dễ thấy nhất. Cùng một pattern lặp lại ở 20 vị trí khác trong
repo, và vài chỗ nguy hiểm hơn — vì chúng trông giống tính năng tốt.

Đáng chú ý: vấn đề `FakeEmbeddings` **đã từng được sửa đúng, kèm test**, ở commit `5fbc555`
(23/8). Hai ngày sau, commit `a07f35a` đảo ngược nó với commit message nghe như một cải tiến
(*"graceful fallback for embedding provider"*). Test cũ vẫn còn và vẫn đang fail trên `main`.

Vì vậy nhánh này đi kèm **59 test mới** khẳng định các hành vi fail-fast. Chúng tồn tại để lần
sau ai đó định "nới lỏng" thì CI báo đỏ, thay vì phát hiện sau vài tháng.
