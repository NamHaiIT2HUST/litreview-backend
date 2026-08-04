# UX & Technical Functional Specification — AI Literature Review Assistant MVP
## Product Flow Overview

MVP hỗ trợ researcher trong giai đoạn:

Research Question → Search → Screening → Quality Check → Library → Export

Mục tiêu: - Tìm paper nhanh hơn. - Lọc paper theo relevance. - Xác minh
chất lượng nguồn. - Tổ chức paper trước Literature Review.

Nguyên tắc: - AI hỗ trợ phân tích, user quyết định Keep/Remove. - Không
tự lấy full text có bản quyền. - Không tự viết Literature Review trong
MVP. - **Mọi con số hiển thị cho user (số kết quả dự kiến, priority
score...) phải tính từ dữ liệu thật, không để AI tự ước lượng/đoán.**

> **[BỔ SUNG KỸ THUẬT — Kiến trúc tổng thể]**
> Hệ thống tách 2 lớp: **Core Backend** (CRUD thuần, không gọi LLM) và **Agent
> Orchestrator** (nơi duy nhất được gọi LLM/embedding — SearchAgent, ScreeningAgent,
> ExtractionAgent, SynthesisAgent). RankingService (tính priority score) nằm ở Core
> Backend vì không cần AI. Core Backend gọi Orchestrator qua job async cho các bước
> chậm (Bulk Screening, Synthesis) — trả `job_id`, frontend poll `GET /jobs/{id}`,
> tránh timeout HTTP khi LLM chậm.
> **[QUYẾT ĐỊNH]** Bước nào chạy đồng bộ, bước nào bắt buộc async — đề xuất: Screening
> 1 paper = đồng bộ; Bulk Screening và Synthesis = async.

------------------------------------------------------------------------

# Module 1: Research Project Setup

## User Goal

Tạo workspace cho một nghiên cứu cụ thể.

## Flow

    Dashboard
     ↓
    New Project
     ↓
    Nhập thông tin nghiên cứu
     ↓
    AI phân tích topic
     ↓
    Sinh keyword gợi ý
     ↓
    User xác nhận
     ↓
    Nhập Inclusion / Exclusion Criteria (tùy chọn, có thể bổ sung sau)
     ↓
    Project được tạo
     ↓
    Search Papers

## User Input

-   Project name
-   Research topic
-   Research question
-   Research field
-   Publication year range
-   **Inclusion criteria** (vd: empirical study, published after 2020,
    university student population)
-   **Exclusion criteria** (vd: review paper, K12 education, opinion
    article)

## System Output

AI tạo: - Research concepts - Keywords - Search terms

## Rule (bổ sung)

-   Nếu user bỏ qua Criteria, hệ thống vẫn cho tạo project bình
    thường nhưng hiển thị cảnh báo: "Screening sẽ chính xác hơn nếu có
    tiêu chí include/exclude." Criteria có thể bổ sung/sửa bất cứ lúc
    nào từ Research Setup, không bắt buộc ngay từ đầu.
-   Criteria được dùng làm input trực tiếp cho AI Screening ở Module 3
    (không phải tính năng tách rời).

## [BỔ SUNG KỸ THUẬT] Data Model

**`projects`**

| field | type | note |
|---|---|---|
| id | UUID PK | |
| name | varchar | |
| research_question | text | |
| research_field | varchar | |
| year_from, year_to | int nullable | |
| criteria_include | text[] | |
| criteria_exclude | text[] | |
| created_at, updated_at | timestamp | |

## [BỔ SUNG KỸ THUẬT] API

```
POST /projects
Request:
{
  "name": "string",
  "research_question": "string",
  "research_field": "string",
  "year_from": 2020, "year_to": 2026,
  "criteria_include": ["empirical study", "university student"],
  "criteria_exclude": ["review paper", "K12"]
}
Response 201:
{
  "id": "uuid",
  "suggested_keywords": ["...", "..."],
  "warning": "Screening sẽ chính xác hơn nếu có tiêu chí include/exclude."  // chỉ có nếu criteria rỗng
}

PATCH /projects/{id}/criteria   → update criteria bất cứ lúc nào, không bắt buộc lúc tạo
```

**Sinh keyword gợi ý**: 1 LLM call đồng bộ (nhanh) — input = research_question +
research_field → output JSON list keyword. Backend phải validate output là JSON hợp lệ
trước khi trả về frontend (LLM có thể trả kèm text thừa/code fence — cần strip & parse an toàn).

------------------------------------------------------------------------

# Module 2: Paper Discovery

## User Goal

Tìm danh sách paper phù hợp.

## Flow

    Research Setup
     ↓
    (Tùy chọn) Gợi ý chiến lược search
     ↓
    Start Search
     ↓
    Generate query
     ↓
    Call academic APIs
     ↓
    Merge results
     ↓
    Deduplicate
     ↓
    Lưu vào Search History
     ↓
    Display paper list
     ↓
    Start Screening

## Data hiển thị

-   Title
-   Author
-   Year
-   Abstract
-   DOI
-   Journal
-   Source

## Search Strategy Suggestion (bổ sung)

-   AI có thể sinh 2-3 chiến lược search dạng boolean query dựa trên
    keyword/criteria.
-   **Số lượng kết quả hiển thị kèm mỗi chiến lược phải lấy từ việc
    gọi API đếm thật (count-only call tới nguồn search), không được để
    AI tự ước lượng con số.** Đây là quy tắc bắt buộc, không phải gợi
    ý — vi phạm sẽ tạo cảm giác chính xác giả cho user.
-   User có thể chọn 1 trong các chiến lược gợi ý hoặc tự nhập query
    riêng.

## Search History (bổ sung — P0)

-   Mỗi lần bấm Search được lưu lại: query đã dùng, số kết quả trả về,
    thời điểm search.
-   User xem lại lịch sử, có thể:
    -   Duplicate 1 lần search cũ để sửa keyword.
    -   So sánh số lượng/nội dung kết quả giữa các lần search khác
        nhau.
-   Mục đích: user không cần tự nhớ "lần trước mình search bằng từ
    khóa gì".

## Deduplication

-   Bản MVP: match theo DOI là chính.
-   Fallback khi thiếu DOI: so khớp title (đã chuẩn hóa lowercase, bỏ
    khoảng trắng thừa) + author + year. Không cần fuzzy matching nâng
    cao ở bản này (để P1).

## [BỔ SUNG KỸ THUẬT] Data Model

**`search_queries`**

| field | type | note |
|---|---|---|
| id | UUID PK | |
| project_id | FK | |
| query_string | text | boolean query thật gửi đi SerpAPI |
| strategy_label | varchar nullable | "Chiến lược 1", hoặc null nếu user tự nhập |
| result_count | int | lấy từ API count-only call thật |
| executed_at | timestamp | |
| is_duplicated_from | FK → search_queries.id nullable | phục vụ "duplicate lần search cũ" |

**`papers`**

| field | type | note |
|---|---|---|
| id | UUID PK | |
| project_id | FK | |
| title, abstract | text | |
| authors | text[] | |
| year | int | |
| doi | varchar nullable | |
| issn | varchar nullable | |
| journal | varchar | |
| source | enum(`scholar`) | |
| dedup_key | varchar | xem thuật toán bên dưới |
| created_at | timestamp | |

*(các field còn lại của `papers` — relevance, scopus, priority_score, pdf_status... — nêu ở
Module 3-6 nơi chúng được set lần đầu)*

## [BỔ SUNG KỸ THUẬT] API

```
POST /projects/{id}/search-strategies
Response 200:
{
  "strategies": [
    { "label": "Chiến lược 1",
      "query_string": "(\"student burnout\" OR \"academic burnout\") AND \"university\"",
      "result_count": 1284 }
  ]
}
```
Pseudocode bắt buộc (tránh lỗi AI tự bịa con số):
```
strategies = llm_generate_boolean_queries(keywords, criteria)  # chỉ sinh QUERY, không sinh số
for s in strategies:
    s.result_count = serpapi.count_only(s.query_string)   # gọi API thật riêng cho từng query
    cache.set(f"count:{hash(s.query_string)}", s.result_count, ttl=24h)
```

```
POST /projects/{id}/search
Request: { "query_string": "...", "strategy_label": "Chiến lược 1" | null }
Response 202: { "job_id": "uuid" }   // async vì có thể nhiều trang kết quả

GET /jobs/{job_id} → khi done: { "status": "done", "search_query_id": "uuid", "paper_count": 87 }
GET /search-queries/{id}/papers   → list Paper đã dedup
GET /projects/{id}/search-history
POST /search-queries/{id}/duplicate   → copy query_string để user sửa, không tự chạy lại
```

## [BỔ SUNG KỸ THUẬT] Thuật toán Deduplication

```
function compute_dedup_key(paper):
    if paper.doi is not null and paper.doi.strip() != "":
        return normalize(paper.doi)   # lowercase, trim
    else:
        title_norm = lowercase(paper.title).replace(multiple_spaces, " ").strip()
        return f"{title_norm}|{paper.authors[0] if paper.authors else ''}|{paper.year}"

for new_paper in fetched_results:
    key = compute_dedup_key(new_paper)
    if key not in existing_keys_in_project:
        insert(new_paper, dedup_key=key)
    # else: bỏ qua, không tạo bản ghi trùng
```
**[QUYẾT ĐỊNH]** Dedup theo phạm vi project hay toàn hệ thống? Đề xuất: theo project (2
project khác nhau có thể cần cùng 1 paper độc lập).

## [BỔ SUNG KỸ THUẬT] SerpAPI integration
-   Cần cache kết quả count theo `hash(query_string)`, TTL 24h — nếu không cache, chi phí
    SerpAPI tăng nhanh vì mỗi lần user mở lại Search Strategy sẽ gọi lại API.
-   Ghi rõ rate limit, chi phí/request, retry policy khi timeout (503 + retry-after, không
    để lỗi rơi thẳng xuống user dạng stacktrace).

------------------------------------------------------------------------

# Module 3: AI Screening Assistant

## User Goal

Quyết định paper nào đáng giữ.

## Flow

    Paper List
     ↓
    Screening Workspace
     ↓
    AI phân tích relevance (dựa trên research question + Criteria)
     ↓
    Hiển thị reason
     ↓
    Tính Priority Score
     ↓
    User Keep / Remove / Maybe (từng paper hoặc chọn hàng loạt)
     ↓
    Lưu decision + decision note

## UI

    Paper Title

    Relevance:
    High / Medium / Low

    Reason:
    Matches:
    - Topic
    - Population

    Mismatch:
    - Different outcome

    Priority: cao / trung bình / thấp

    Actions:
    [Keep]
    [Remove]
    [Maybe]

    (khi Remove) Ghi chú lý do: [free text, tùy chọn]

## Bulk Actions (bổ sung — P0)

-   User có thể chọn nhiều paper cùng lúc (checkbox) để:
    -   Keep hàng loạt.
    -   Remove hàng loạt.
    -   Thêm hàng loạt vào Library.
-   Cần giới hạn số lượng paper xử lý cùng lúc trong 1 request (tránh
    timeout khi user chọn quá nhiều, vd giới hạn ở mức hợp lý theo
    năng lực backend).

## Priority Ranking (bổ sung — P0)

-   Không phải điểm relevance mới, mà là **composite score tính từ dữ
    liệu đã có sẵn**, không gọi thêm AI riêng cho bước này:
    -   Trọng số theo relevance bucket (High/Medium/Low).
    -   Có/không Scopus indexed (lấy từ Module 4, nếu đã chạy).
    -   Độ mới của paper (năm xuất bản).
-   Mục đích: trả lời câu hỏi "nên đọc paper nào trước", khác với câu
    hỏi "paper nào liên quan" mà relevance bucket đã trả lời.

## Screening History (bổ sung)

-   Mọi quyết định Keep/Remove/Maybe được lưu lại kèm: paper nào, quyết
    định gì, lý do (AI reason + user note nếu có), thời điểm quyết
    định.
-   User có thể xem lại và đổi quyết định bất kỳ lúc nào; lịch sử cũ
    vẫn được giữ, không ghi đè mất.

## Rule

-   AI không tự quyết định Keep/Remove.
-   Không hiển thị % similarity hay bất kỳ con số AI tự tin cậy nào
    không kiểm chứng được.
-   Reason phải dựa trên abstract và Criteria, không suy diễn thông
    tin ngoài văn bản nguồn.
-   Nếu abstract quá ngắn để đánh giá đáng tin cậy, hệ thống hiển thị
    cảnh báo "Không đủ thông tin để đánh giá chính xác" thay vì vẫn
    đưa ra bucket như bình thường.

## [BỔ SUNG KỸ THUẬT] Data Model bổ sung cho `papers`

| field | type | note |
|---|---|---|
| relevance_bucket | enum(`high`,`medium`,`low`,`insufficient_info`) nullable | |
| relevance_reason | jsonb | `{matches: [...], mismatches: [...]}` |
| priority_score | float nullable | công thức bên dưới |
| screening_decision | enum(`keep`,`remove`,`maybe`,`pending`) default `pending` | |

**`screening_history`** (append-only, không update/delete — mỗi lần đổi quyết định = 1 row mới)

| field | type | note |
|---|---|---|
| id | UUID PK | |
| paper_id | FK | |
| decision | enum(`keep`,`remove`,`maybe`) | |
| ai_reason | jsonb nullable | snapshot lý do AI tại thời điểm đó |
| user_note | text nullable | |
| decided_at | timestamp | |

## [BỔ SUNG KỸ THUẬT] API

```
POST /papers/{id}/screen
Response 200:
{
  "relevance_bucket": "high" | "medium" | "low" | "insufficient_info",
  "reason": { "matches": ["Topic: đúng chủ đề burnout"], "mismatches": ["Outcome khác research question"] }
}
```
Rule bắt buộc trong prompt LLM: input CHỈ gồm abstract + criteria + research_question, không
suy diễn ngoài văn bản. Nếu `len(abstract) < N ký tự` (đề xuất 200) → trả thẳng
`insufficient_info`, **không gọi LLM** (tiết kiệm chi phí, tránh AI đoán bừa từ dữ liệu thiếu).
Output không được chứa % similarity/confidence số.

```
POST /papers/{id}/screening-decision
Request: { "decision": "keep"|"remove"|"maybe", "note": "string | null" }
# Backend: insert 1 row mới vào screening_history, update papers.screening_decision

POST /papers/bulk-decision
Request: { "paper_ids": ["uuid", ...], "decision": "keep" }
```
**[QUYẾT ĐỊNH]** Giới hạn bulk action cụ thể — đề xuất **tối đa 50 paper/request**; nếu user
chọn nhiều hơn, frontend tự chia batch tuần tự + hiển thị progress bar (400 Bad Request kèm
limit cụ thể nếu vượt).

## [BỔ SUNG KỸ THUẬT] Công thức Priority Score

```
relevance_weight = { high: 3, medium: 2, low: 1, insufficient_info: 0 }
scopus_weight     = { indexed: 2, undetermined: 1, not_indexed: 0 }
recency_weight    = clamp((paper.year - (current_year - 10)) / 10, 0, 1)

priority_score = (relevance_weight[bucket] * 0.5)
               + (scopus_weight[status] * 0.3)
               + (recency_weight * 0.2)
# normalize 0-1, hiển thị bucket "cao/trung bình/thấp" theo ngưỡng — KHÔNG hiển thị số thô
```
**[QUYẾT ĐỊNH]** Trọng số 0.5/0.3/0.2 nên để config được (không hardcode), nhóm có thể chỉnh
sau khi thử nghiệm thực tế.

Trigger tính lại: viết 1 hàm chung `recompute_priority(paper_id)`, gọi ở cuối cả flow Screening
(Module 3) và Quality Check (Module 4) — tránh trùng logic ở 2 chỗ.

------------------------------------------------------------------------

# Module 4: Quality Verification

## User Goal

Biết paper có nguồn đáng tin cậy.

## Flow

    Keep Paper
     ↓
    Quality Check (chỉ chạy cho paper đã Keep, không chạy toàn bộ kết quả search)
     ↓
    Scopus verification (match ISSN)
     ↓
    Kiểm tra Coverage Year
     ↓
    Open Access check
     ↓
    Update badge
     ↓
    Library

## Hiển thị

    Scopus:
    ✓ Indexed / ✗ Not indexed / – Không xác định

    Quartile:
    Q1 (nếu có)

    Coverage year:
    OK / Ngoài phạm vi index / Không áp dụng

    Access:
    Gold OA / Hybrid OA / Bronze / Green / Closed / Không xác định

## Coverage Year Check (bổ sung)

-   Một tạp chí có thể được Scopus index nhưng chỉ từ 1 năm nhất định
    trở đi. Nếu paper xuất bản trước mốc đó, hệ thống phải hiển thị rõ
    "Ngoài phạm vi index của Scopus tại thời điểm xuất bản" — không
    được chỉ ghi "Indexed" chung chung dựa trên tên tạp chí, vì điều
    đó gây hiểu lầm về độ tin cậy thật của chính bài báo đó.

## Rule xử lý trường hợp không xác định (bổ sung — quan trọng)

-   Nếu paper không có ISSN, hoặc ISSN không match được với Scopus
    Source List (thường gặp với conference paper), trạng thái hiển thị
    phải là **"Không xác định"**, tuyệt đối không được mặc định là
    "Not indexed". Đây là 2 trạng thái có ý nghĩa khác nhau và dev cần
    phân biệt rõ trong logic, không gộp chung một nhánh else.
-   Tương tự với Open Access: nếu chưa tra được OA status (do thiếu
    DOI hoặc lỗi gọi API), hiển thị "Không xác định", không mặc định
    "Closed".

## [BỔ SUNG KỸ THUẬT] Data Model

**`scopus_sources`** (import định kỳ từ file Excel Scopus — job nội bộ, không phải API user-facing)

| field | type |
|---|---|
| issn | varchar (normalized) |
| title | varchar |
| quartile | varchar |
| coverage_year_start | int |
| coverage_year_end | int |

Bổ sung field cho `papers`: `scopus_status` enum(`indexed`,`not_indexed`,`undetermined`)
default `undetermined`; `scopus_quartile` nullable; `coverage_year_status`
enum(`ok`,`out_of_coverage`,`not_applicable`) nullable; `oa_status`
enum(`gold`,`hybrid`,`bronze`,`green`,`closed`,`undetermined`) default `undetermined`.

## [BỔ SUNG KỸ THUẬT] Thuật toán matching (đặc tả rõ để dev không code sai)

```
function import_scopus_excel(file):
    for row in excel_rows:
        upsert scopus_sources:
            issn = normalize(row.issn)   # bỏ dấu "-", khoảng trắng
            title = row.title
            quartile = row.quartile
            coverage_year_start = row.coverage_start
            coverage_year_end = row.coverage_end or current_year

function quality_check(paper):
    if paper.issn is null:
        paper.scopus_status = "undetermined"
    else:
        source = scopus_sources.find_by_issn(normalize(paper.issn))
        if source is null:
            paper.scopus_status = "undetermined"   # KHÔNG gán "not_indexed"
        else:
            paper.scopus_status = "indexed"
            paper.scopus_quartile = source.quartile
            paper.coverage_year_status = "out_of_coverage" if paper.year < source.coverage_year_start else "ok"

    if paper.doi is null:
        paper.oa_status = "undetermined"
    else:
        oa_result = call_oa_api(paper.doi)   # vd Unpaywall
        paper.oa_status = "undetermined" if (oa_result is error or timeout) else oa_result.status

    recompute_priority(paper.id)
```

**[QUYẾT ĐỊNH]** `not_indexed` chỉ nên set khi Excel Scopus xác nhận rõ ràng journal đó KHÔNG
nằm trong danh sách hiện hành (không chỉ đơn giản "không tìm thấy ISSN"). Nếu Excel chỉ chứa
danh sách journal ĐANG được index, thì mọi trường hợp không match = `undetermined`, và enum
`not_indexed` gần như không bao giờ tự động set — cần nhóm xác nhận lại cấu trúc file Excel
trước khi code phần này.

```
POST /papers/{id}/quality-check   → trigger hàm trên, response trả full paper object đã update
```

------------------------------------------------------------------------

# Module 5: Library Management

## User Goal

Quản lý các paper đã chọn.

## Flow

    Keep Paper + Quality Check xong
     ↓
    Vào Library
     ↓
    Nếu Open Access → hệ thống tự động fetch full-text (không cần user thao tác)
     ↓
    Nếu không Open Access → hiển thị "Open source" (link publisher),
    user tự tải PDF nếu có quyền, rồi Upload thủ công
     ↓
    Ready for analysis (khi đã có PDF, dù tự động hay thủ công)

## Paper Status (đã tách lại — sửa lỗi gộp 2 khái niệm)

Bản gốc gộp 4 trạng thái (Metadata Only / OA Full-text Available /
User Uploaded PDF / Extraction Completed) vào 1 enum duy nhất — điều
này gây mâu thuẫn logic vì một paper có thể "đã upload PDF" nhưng
"chưa extraction xong" cùng lúc, không thuộc rõ case nào trong 4 giá
trị trên. Tách thành 2 field độc lập:

    pdf_status:
    - not_uploaded       (chưa có file nào)
    - oa_auto_fetched     (hệ thống tự lấy vì paper là OA)
    - user_uploaded       (user tự tải lên)

    extraction_status:
    - not_extracted       (chưa chạy AI trích xuất)
    - extracted            (đã có Objective/Method/Finding/Gap/Limitation)

Hai field này độc lập với nhau — UI hiển thị tổ hợp thực tế thay vì cố
ép vào 1 nhãn duy nhất, ví dụ: "Đã có full-text (tự động) · Chưa
extraction" là một trạng thái hợp lệ và cần hiển thị đúng như vậy.

## Rule

-   Paper không có quyền truy cập vẫn được giữ trong Library ở trạng
    thái `pdf_status = not_uploaded`, không bị chặn hay ẩn khỏi danh
    sách — vẫn dùng được cho quản lý và export citation.

## [BỔ SUNG KỸ THUẬT] State machine cho `pdf_status`

```
not_uploaded ──(OA check = gold/hybrid/bronze/green)──▶ oa_auto_fetched
not_uploaded ──(user upload PDF thủ công)──▶ user_uploaded
# Không có transition ngược lại. Nếu fetch OA thất bại (link chết, timeout):
# giữ nguyên not_uploaded, không set trạng thái lỗi riêng, chỉ log lỗi backend, không chặn user.
```

## [BỔ SUNG KỸ THUẬT] API

```
GET /library?project_id=xxx&filter=pdf_status:not_uploaded   → filter/sort theo mọi field của papers
```
Khi `oa_status` chuyển thành gold/hybrid/bronze/green (từ Module 4), backend tự trigger job
fetch full-text (async), cập nhật `pdf_status = oa_auto_fetched` khi xong.

------------------------------------------------------------------------

# Module 6: PDF Upload & Extraction

## User Goal

Trích xuất thông tin từ paper.

## Flow

    Library (pdf_status != not_uploaded)
     ↓
    (Nếu chưa có PDF) Upload PDF thủ công
     ↓
    AI Extract
     ↓
    Display summary
     ↓
    extraction_status = extracted

## Output

-   Objective
-   Method
-   Finding
-   Limitation
-   Research Gap

## Rule

-   Extraction chỉ chạy khi `pdf_status` khác `not_uploaded` — không
    có PDF thì không có gì để trích xuất, hệ thống không được gọi AI
    trong trường hợp này (tránh lãng phí gọi API vô ích).

## [BỔ SUNG KỸ THUẬT] Data Model

**`extractions`**

| field | type |
|---|---|
| paper_id | FK PK |
| objective, method, finding, limitation, research_gap | text |
| extracted_at | timestamp |

## [BỔ SUNG KỸ THUẬT] API

```
POST /papers/{id}/upload-pdf   (multipart/form-data)
Response: { "pdf_status": "user_uploaded", "pdf_url": "..." }

POST /papers/{id}/extract
Precondition: pdf_status != "not_uploaded"  → nếu vi phạm, trả 409 Conflict, KHÔNG gọi LLM
Response 202: { "job_id": "uuid" }   # async vì PDF dài có thể chậm

GET /jobs/{id} → khi done: { "extraction": { objective, method, finding, limitation, research_gap } }
```
Pipeline nội bộ: PDF → text theo trang (giữ page number để tái dùng ở Module 8) → LLM extract
theo 5 field cố định → validate JSON → lưu `extractions`.

------------------------------------------------------------------------

# Module 7: Citation Export

## Flow

    Library
     ↓
    Select papers
     ↓
    Choose format
     ↓
    Generate file
     ↓
    Download

## Format

-   BibTeX
-   RIS
-   CSV

## [BỔ SUNG KỸ THUẬT] API

```
POST /export
Request: { "paper_ids": ["uuid"], "format": "bibtex"|"ris"|"csv" }
Response 200: file stream, Content-Disposition: attachment
```
Không cần AI. Map trực tiếp field trong `papers` sang format tương ứng, dùng thư viện có sẵn
cho BibTeX/RIS (không tự parse bằng tay).

------------------------------------------------------------------------

# Module 8: Upload & Synthesis (MỚI — thiết kế đề xuất, chưa có trong bản gốc)

## User Goal

Upload nhiều paper, nhận bản tổng quan tài liệu (literature review) có trích dẫn — người
dùng bấm vào trích dẫn là thấy ngay đoạn gốc, không cần tự đối chiếu lại PDF.

## Flow

    Library (chọn N paper đã có PDF)
     ↓
    Tạo Synthesis Session
     ↓
    Parse PDF theo trang → Chunk → Embed (nếu paper chưa có chunk)
     ↓
    SynthesisAgent viết review (ưu tiên dùng Extraction có sẵn thay vì đọc lại toàn PDF)
     ↓
    Backend map marker trích dẫn → offset thật trong PDF gốc
     ↓
    Hiển thị review, click trích dẫn → highlight + nhảy đúng trang/đoạn

## [BỔ SUNG KỸ THUẬT] Data Model

**`synthesis_sessions`**

| field | type |
|---|---|
| id | UUID PK |
| project_id | FK |
| paper_ids | UUID[] |
| status | enum(`processing`,`done`,`failed`) |
| review_markdown | text nullable — chứa marker `[[cite:xxx]]` inline |
| created_at | timestamp |

**`citations`**

| field | type |
|---|---|
| id | UUID PK |
| synthesis_session_id | FK |
| paper_id | FK |
| citation_marker | varchar (vd `cite_001`) |
| review_char_start, review_char_end | int — vị trí trong `review_markdown` |
| source_page | int |
| source_char_start, source_char_end | int — vị trí trong text đã parse của PDF gốc |
| quoted_snippet | text — đoạn text gốc, để hiển thị preview không cần load lại PDF |

**`pdf_chunks`** (phục vụ RAG)

| field | type |
|---|---|
| id | UUID PK |
| paper_id | FK |
| chunk_text | text |
| page | int |
| char_start, char_end | int |
| embedding | vector(N) — lưu trong Qdrant, Postgres chỉ giữ reference id |

## [BỔ SUNG KỸ THUẬT] Pipeline chi tiết

```
1. User chọn N paper đã có pdf_status != not_uploaded
2. Với mỗi paper chưa có pdf_chunks:
     text_by_page = parse_pdf(pdf_url)   # giữ page number
     chunks = split_by_paragraph(text_by_page, max_tokens=500, overlap=50)
     for chunk in chunks:
         embedding = embed(chunk.text)
         store in Qdrant với payload = {paper_id, page, char_start, char_end}
3. SynthesisAgent nhận: research_question + extractions[] của các paper đã chọn
   (ưu tiên dùng extraction có sẵn từ Module 6 thay vì đọc lại toàn bộ PDF — tiết kiệm token)
4. LLM sinh review theo cấu trúc: Introduction → Theme 1..N (gom theo research_gap/finding
   tương đồng) → Common gaps → Conclusion. Output bắt buộc: mỗi câu trích dẫn kèm marker
   dạng [[cite:paper_id:chunk_id]]
5. Backend parse marker ra khỏi review_markdown:
   - Query lại Qdrant/pdf_chunks để lấy source_page + char offset thật
   - Insert vào bảng citations (review offset + source offset)
   - Thay marker thô bằng ký hiệu hiển thị [1], [2]...
6. Trả synthesis_session hoàn chỉnh cho frontend
```

## [BỔ SUNG KỸ THUẬT] API

```
POST /synthesis-sessions
Request: { "project_id": "uuid", "paper_ids": ["uuid", ...] }
Response 202: { "job_id": "uuid" }

GET /synthesis-sessions/{id}
Response khi done:
{
  "status": "done",
  "review_markdown": "...Sinh viên đại học có xu hướng burnout cao hơn[1]...",
  "citations": [
    { "marker_display": "[1]", "paper_id": "uuid", "paper_title": "...",
      "source_page": 4, "quoted_snippet": "Results indicate that undergraduate students report...",
      "source_char_start": 1200, "source_char_end": 1350 }
  ]
}
```

## [BỔ SUNG KỸ THUẬT] Frontend rendering (click-to-verify)

-   Render `review_markdown`, thay `[1]` `[2]`... bằng `<span data-citation-id="...">` có
    style highlight nhẹ (underline/background màu).
-   Click vào → mở panel bên phải, load `quoted_snippet` (đã có sẵn trong response, không
    cần gọi lại API) → dùng `source_page` để nhảy đúng trang trong PDF viewer.
-   **Không cần OCR bounding-box pixel-level cho MVP** — chỉ cần nhảy đúng trang + hiển thị
    `quoted_snippet` để user đối chiếu bằng mắt là đủ đạt yêu cầu "click thấy ngay, không cần
    check nhiều". Bounding-box chính xác là P1.

## Rule

-   Extraction chưa có cho paper nào đó → **[QUYẾT ĐỊNH]** tự động chạy Extraction trước khi
    Synthesis, hay trả 400 yêu cầu user extract trước.
-   Giới hạn số paper/synthesis session — đề xuất tối đa 15 (nhiều hơn sẽ chậm và loãng bài review).

## Điểm khác biệt so với NotebookLM

-   NotebookLM: trả lời từng câu hỏi rời rạc, không có cấu trúc lit-review cố định.
-   Hệ thống này: sinh 1 bài có bố cục chuẩn academic (theo Theme/Gap), tái dùng structured
    extraction đã có sẵn nên nhất quán hơn giữa các lần chạy.
-   Mở rộng P1 (không cam kết MVP): bảng so sánh phương pháp giữa các paper, tự phát hiện
    mâu thuẫn finding giữa 2 paper.

------------------------------------------------------------------------

# Complete User Journey

    Create Project
     ↓
    Research Setup (kèm Inclusion/Exclusion Criteria)
     ↓
    Generate Search Strategy (số liệu lấy từ API thật)
     ↓
    Search Papers (lưu Search History)
     ↓
    AI Screening (kèm Priority Ranking, Bulk Actions)
     ↓
    Keep / Remove / Maybe (kèm decision note)
     ↓
    Quality Verification (Scopus + Coverage Year + OA)
     ↓
    Library (tự động fetch nếu OA)
     ↓
    Upload PDF (nếu cần)
     ↓
    Extract Information
     ↓
    Upload & Synthesis (Module 8 — tổng quan tài liệu có trích dẫn)
     ↓
    Export Citation

------------------------------------------------------------------------

# Navigation

    Research Workspace

    ├── Overview
    ├── Research Setup
    ├── Search Papers
    ├── Screening
    ├── Quality Check
    ├── Library
    ├── Synthesis        ← mới, Module 8
    └── Export

------------------------------------------------------------------------

# [BỔ SUNG KỸ THUẬT] Yêu cầu phi chức năng & error handling chung

| Tình huống | Xử lý |
|---|---|
| SerpAPI timeout/rate-limit | 503 + retry-after, không để lỗi rơi thẳng dạng stacktrace |
| LLM trả JSON không hợp lệ (screening/extraction) | retry 1 lần với prompt nhắc format; vẫn fail → trả `insufficient_info`/`not_extracted`, log để review — không giả lập dữ liệu |
| Extract khi `pdf_status = not_uploaded` | 409 Conflict, chặn ở Core Backend |
| Quality check thiếu ISSN/DOI | không lỗi — set `undetermined`, trả 200 bình thường |
| Bulk action vượt giới hạn N | 400 Bad Request kèm limit cụ thể |

-   Cache SerpAPI theo `hash(query_string)`, TTL 24h.
-   Mọi bước gọi LLM đi qua 1 wrapper chung: retry tối đa 1-2 lần, timeout cứng, log
    input/output — không gọi LLM rải rác nhiều nơi trong code.
-   Giới hạn upload PDF: đề xuất 20MB/file.
-   PDF user upload chỉ truy cập được trong phạm vi project đó, không public URL trực tiếp.

# [BỔ SUNG KỸ THUẬT] Checklist nghiệm thu (Definition of Done)

- [ ] M1: Tạo project không có criteria vẫn thành công, có warning đúng text.
- [ ] M2: `result_count` khớp với số API trả thật.
- [ ] M2: Dedup không tạo trùng khi search lại cùng keyword 2 lần.
- [ ] M3: Abstract < ngưỡng ký tự → ra `insufficient_info`, không gọi LLM (kiểm tra qua log).
- [ ] M3: Bulk action vượt giới hạn → lỗi rõ ràng, không timeout server.
- [ ] M4: Paper không ISSN → `undetermined`, không bao giờ tự thành `not_indexed`.
- [ ] M5: OA fetch fail → im lặng giữ `not_uploaded`, không crash flow.
- [ ] M6: Gọi extract khi chưa upload → 409, không tốn LLM call.
- [ ] M8: Mỗi citation trong review đều mở đúng trang + đúng đoạn snippet.

# [BỔ SUNG KỸ THUẬT] Việc cần chốt trước khi code

1.  Bước AI nào async (job+poll) vs đồng bộ.
2.  Dedup theo phạm vi project hay toàn hệ thống.
3.  Giới hạn bulk action = 50 paper/request (hoặc số khác nhóm tự quyết).
4.  Trọng số công thức priority score có để config được không.
5.  Nguồn Excel Scopus có phân biệt được "not_indexed" thật hay chỉ có "undetermined" luôn xảy ra.
6.  Synthesis khi thiếu extraction: tự chạy trước hay bắt user extract trước.
