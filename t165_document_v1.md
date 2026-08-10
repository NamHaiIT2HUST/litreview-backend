# T165 — Đặc tả UX và Technical Functional Specification (MVP)

## 1. Mục tiêu và quyết định sản phẩm

T165 là trợ lý tìm kiếm, xác minh và tổ chức tài liệu cho sinh viên cao học,
nghiên cứu sinh và researcher đang làm literature review.

Luồng cốt lõi của MVP:

`Research Setup → Google Scholar Search → Scopus Cross-check → Review results → Screening → Library → PDF/Ingestion → Synthesis → Export`

Quyết định tìm kiếm:

- Google Scholar qua SerpApi là nguồn tìm kiếm chính. Hệ thống giữ nguyên thứ tự
  xếp hạng và giới hạn do Google Scholar trả về; không tự xây lại thuật toán rank.
- Hệ thống lấy Top 20 từ Google Scholar. Backend chỉ lấy đúng 20 kết quả đầu theo thứ tự
  Google Scholar trả về, sau đó đối chiếu từng bài với danh mục Scopus nội bộ bằng ISSN/EISSN
  và tên tạp chí.
- Kết quả hiển thị mặc định là các bài đã đối chiếu được với Scopus. Không match do
  thiếu dữ liệu không được gán nhầm là “không đạt”; trạng thái kỹ thuật vẫn là
  `undetermined` và có thể mở rộng thành bộ lọc ba trạng thái ở P1.
- OpenAlex/Semantic Scholar chỉ dùng để bổ sung abstract, DOI, ISSN hoặc fallback khi
  SerpApi không khả dụng; không được thay thế thứ tự Google Scholar khi GS đã chạy.
- Mọi số đếm hiển thị cho user phải lấy từ response thật của provider hoặc database,
  không do LLM ước lượng.
- AI hỗ trợ giải thích, sinh query và screening; user là người quyết định giữ/bỏ.

## 2. Phạm vi MVP

### Must have

1. Tạo project và lưu research question, field, năm, inclusion/exclusion criteria.
2. Tìm trên Google Scholar với Top 20, lưu search history.
3. Cross-check Scopus ngay trong pipeline search và hiển thị badge minh bạch.
4. Xem abstract/metadata, giữ thứ tự GS, loại duplicate theo DOI hoặc title-author-year.
5. Screening AI có lý do, quyết định Keep/Remove/Maybe và bulk action.
6. Library, upload PDF hợp pháp, parse theo trang và lưu chunk có provenance.
7. Synthesis có citation traceability ở mức MVP và export metadata.

### Không thuộc MVP

Không tự lấy full text có bản quyền, không tự nộp bài, không collaboration nhiều người,
không fuzzy dedup nâng cao, không tự viết review không có nguồn truy vết.

## 3. User flow và navigation

Nguyên tắc thiết kế UI: không ánh xạ cứng “mỗi module kỹ thuật = một màn hình”.
Module trong tài liệu này là năng lực xử lý hoặc cụm nghiệp vụ bên dưới backend/UI.
Navigation là cách gom các năng lực đó thành workflow ít bước, dễ thao tác và ít chuyển tab.
Những tính năng nào thường được dùng liền nhau thì đặt chung trong một navigation, chỉ tách
ra khi user có một ngữ cảnh làm việc thật sự khác.

### Luồng chính

1. User vào Overview, tạo hoặc mở một Research Project.
2. Research Setup thu thập câu hỏi nghiên cứu và criteria; có thể bổ sung criteria sau.
3. User mở Search & Verify, nhập query hoặc chọn query gợi ý.
4. User bấm Search; hệ thống mặc định lấy Top 20 từ Google Scholar.
5. Backend gọi Google Scholar, enrich metadata nếu thiếu, deduplicate, cross-check Scopus.
6. UI hiển thị summary `found`, `confirmed`, `undetermined` và danh sách đã đối chiếu.
7. User xem abstract, lọc và đưa bài vào Screening/Library.
8. Screening AI phân tích relevance; user quyết định Keep/Remove/Maybe.
9. Bài Keep đi vào Quality/Library; user upload PDF nếu cần đọc sâu.
10. Ingestion tạo chunk và extraction; Synthesis tạo bản tổng hợp có citation.
11. Export BibTeX/CSV/Markdown và các định dạng mở rộng ở P1.

### Navigation đề xuất — gộp capability để giảm thao tác

| Navigation | Capability tích hợp | Chức năng và tác dụng |
|---|---|---|
| Overview | dashboard + project progress | tiến độ project, số bài đã tìm/đã xác nhận/Keep, shortcut bước tiếp theo |
| Research Setup | project setup + criteria + query suggestion | project, research question, field, năm, criteria, keyword/query suggestion |
| Search & Verify | Google Scholar search + Scopus cross-check + dedup + history + quick quality view | tìm Top 20 trên Google Scholar, đối chiếu Scopus ngay, filter badge, xem abstract và lịch sử search trong cùng workspace |
| Screening | AI relevance + decision workflow | AI relevance, lý do matches/mismatch, Keep/Remove/Maybe, bulk và history |
| Library & Reader | saved papers + upload + PDF reader + provenance | danh sách bài Keep, trạng thái PDF/extraction, upload, mở abstract/PDF và provenance |
| Synthesis | Workspace/RAG + extraction insight + citation trace | chọn bài, extraction, hỏi đáp closed-domain và tổng hợp có citation |
| Export | metadata export + citation export + draft export | xuất metadata, citation và bản thảo |

`Search & Verify` là navigation gộp bắt buộc: Quality Check không còn là bước người dùng
phải chạy riêng cho các bài vừa search. Có thể giữ API `POST /papers/{id}/quality-check`
cho re-check thủ công, nhưng UI chính gọi pipeline Search → Verify.

Các module/capability kỹ thuật bên dưới không nhất thiết xuất hiện thành navigation riêng.
Ví dụ `Dedup`, `Scopus Matcher`, `Coverage Check`, `Provider Fallback` là capability trong
Search & Verify; `PDF Parser`, `Chunking`, `Embedding` là capability trong Library & Reader
hoặc Synthesis tùy ngữ cảnh.

## 4. Đặc tả capability/module kỹ thuật theo navigation

Các mục M1-M6 dưới đây mô tả cụm chức năng và công nghệ xử lý. Đây không phải yêu cầu
tách thành sáu màn hình riêng; UI cuối cùng ưu tiên số navigation ít hơn, gom các thao tác
liên tiếp vào cùng một màn.

### M1 — Research Setup

**UI:** form project name, research question, research field, year range, inclusion và
exclusion criteria; hiển thị keyword gợi ý và nút “Dùng query này”. Criteria không bắt buộc
khi tạo nhưng phải cảnh báo screening sẽ kém chính xác hơn.

**Xử lý:** FastAPI/SQLAlchemy lưu `projects`. LLM chỉ sinh keyword/query dạng JSON;
backend strip code fence, parse và validate schema. Không lưu output không hợp lệ.

**API:** `GET/PUT /projects/{id}`, `PATCH /projects/{id}/criteria`,
`POST /projects/{id}/suggest-keywords`.

### M2 — Search & Verify (navigation trọng tâm, gộp nhiều capability)

**UI:** một search bar, query strategy chips, bộ lọc tác giả/năm, nút Search,
status banner cho provider, summary cards và bảng kết quả Top 20. Mỗi dòng có title,
authors, year, journal, abstract/snippet, DOI, Scopus badge, coverage badge, OA badge,
link nguồn và nút Add to Screening/Library. History nằm ở drawer bên phải, có duplicate.

Các capability đặt chung trong navigation này:

- Search Google Scholar: lấy Top 20 và giữ nguyên thứ tự GS.
- Metadata enrichment: bổ sung DOI, abstract, ISSN/EISSN khi thiếu.
- Scopus cross-check: đối chiếu nguồn/tạp chí bằng ISSN/EISSN/title.
- Dedup: tránh trùng DOI hoặc title-author-year trong cùng project.
- Quick quality view: hiển thị badge `indexed`, `coverage`, `undetermined`; cho phép re-check
  từng bài khi cần nhưng không buộc user sang tab khác.
- Search history: xem lại query, provider, limit, counters và duplicate state trong cùng màn.

**Pipeline kỹ thuật:**

```text
query + fixed limit(20)
  → SerpApi engine=google_scholar
  → giữ nguyên thứ tự organic_results
  → enrich thiếu abstract/DOI/ISSN bằng OpenAlex/Semantic Scholar
  → normalize DOI/ISSN/EISSN
  → deduplicate trong project
  → match scopus_sources theo ISSN/EISSN, fallback title nếu dữ liệu cho phép
  → coverage-year check
  → trả kết quả + counts thật
```

`total_found` là số bài GS trả về trước đối chiếu; `total_confirmed` là số match Scopus;
`total_undetermined` là số không đủ dữ liệu để kết luận. Chế độ MVP mặc định chỉ render
`indexed` và cho phép mở “xem các bài chưa xác định”; tuyệt đối không gọi đó là
`not_indexed` nếu source list không xác nhận rõ.

**Search strategy:** LLM sinh tối đa 3 query, chỉ sinh query. Mỗi query gọi count thật
qua SerpApi và cache theo hash 24 giờ. Query suggestion không được làm thay đổi ranking.

**Dedup:** ưu tiên `normalize(doi)`, fallback
`lowercase(title)|first_author|year`; phạm vi dedup là project.

**API mục tiêu:**

```text
POST /projects/{id}/search-strategies
POST /projects/{id}/search  { query_string, include_undetermined?: bool }
GET  /projects/{id}/search-history
GET  /search-queries/{id}/papers
POST /search-queries/{id}/duplicate
```

Response search tối thiểu:

```json
{
  "provider": "google_scholar",
  "limit": 20,
  "total_found": 20,
  "total_confirmed": 6,
  "total_undetermined": 14,
  "papers": []
}
```

**Lỗi:** thiếu SerpApi key hoặc quota thì fallback S2/OpenAlex và banner rõ “Fallback”; timeout
trả lỗi có mã/retry, không stacktrace. Provider fallback không được gắn nhãn là kết quả GS.

### M3 — Screening

**UI:** bảng có checkbox, relevance High/Medium/Low/Insufficient info, lý do matches/mismatch,
decision và note. Toolbar có Keep/Remove/Maybe/Add to Library hàng loạt, tối đa 50/request.
History là append-only và cho phép đổi quyết định.

**Xử lý:** LLM chỉ nhận research question + criteria + abstract. Abstract ngắn hơn ngưỡng
cấu hình (mặc định 200 ký tự) trả `insufficient_info`, không gọi LLM. Không hiển thị phần trăm
similarity/confidence. Priority bucket nếu dùng chỉ là hàm backend từ relevance, Scopus và
recency; không được mô tả là AI score.

**API hiện có:** `POST /papers/{id}/screen`,
`POST /papers/{id}/screening-decision`, `POST /papers/bulk-decision`.

### M4 — Library & Reader (gộp quản lý bài, upload và đọc sâu)

**UI:** danh sách bài Keep, filter theo Scopus/decision/PDF/extraction, upload PDF, mở reader
hai pane (document và notes/citation). Bài không có quyền truy cập vẫn giữ metadata trong Library.

**Xử lý:** `pdf_status` và `extraction_status` độc lập. PyMuPDF/pypdf parse theo trang;
chunk lưu `paper_id`, `page_number`, `char_start`, `char_end`, text và embedding vào Chroma/Qdrant.
Upload giới hạn 20 MB/file, đường dẫn không public và scoped theo project. Extraction chỉ chạy
khi đã có PDF.

**API hiện có:** `POST /workspace/upload`, `GET /workspace/test-search`,
`POST /workspace/chat`.

### M5 — Synthesis

**UI:** chọn tối đa 15 bài đã Keep/extracted, xem outline, draft, citation panel và click citation
để xem snippet/trang nguồn. Chat chỉ trả lời từ tài liệu đã ingest.

**Xử lý:** LangGraph điều phối Outline → Retrieve → Draft. Mỗi claim phải gắn chunk citation;
claim không có evidence bị loại hoặc đánh dấu cần kiểm tra. Integrity/retraction check và
verification layer là mục P1 nếu chưa có connector Crossref hoàn chỉnh. Không gọi LLM một phát
cho toàn bộ review.

### M6 — Export

MVP xuất CSV/BibTeX metadata đã xác minh và Markdown có citation. P1 bổ sung CSL APA/IEEE/MLA,
Word/PDF, version history và Zotero API. Không ghi đè bản export cũ.

## 5. Data model chuẩn

- `projects`: id, name, research_question, research_field, year_from/to, criteria_include/exclude.
- `search_queries`: project_id, query_string, provider, requested_limit, total_found,
  total_confirmed, total_undetermined, executed_at, duplicate_source_id.
- `papers`: title, authors, year, abstract, DOI, ISSN/EISSN, journal, source_rank,
  dedup_key, scopus_status, coverage_year_status, oa_status, screening_decision,
  pdf_status, extraction_status.
- `scopus_sources`: normalized ISSN/EISSN, title, active status, coverage ranges; quartile
  chỉ lưu khi có dataset CiteScore hợp lệ, không bịa từ Source Title List.
- `screening_history`: paper_id, decision, ai_reason, user_note, decided_at.
- `pdf_chunks`: paper_id, page_number, char offsets, text, embedding.
- `extractions`, `synthesis_sessions`, `citations`: lưu kết quả có provenance.

## 6. Đối chiếu với code hiện tại

### Đã có nền tảng

- `src/services/scholar_api.py`: SerpApi Google Scholar, OpenAlex/Semantic Scholar enrichment,
  và fallback provider.
- `src/services/scopus_matcher.py`: normalize ISSN, match ISSN/EISSN/title, parse coverage
  ranges và trạng thái `indexed/undetermined`; chưa có quartile đáng tin nếu dataset không có.
- `src/api/routes.py`: search, search strategy/count, history, duplicate, quality-check,
  upload và workspace chat endpoints.
- `src/api/screening_routes.py` và `screening_service.py`: AI screening, decision history,
  bulk max 50, priority recompute.
- React đã có các màn Search, Screening, Quality, Library/Upload, Workspace/Synthesis, Export
  placeholder và Navbar gồm các bước chính.

### Chưa khớp hoặc cần hoàn thiện

1. `search_papers_auto` hiện có thể ưu tiên Semantic Scholar khi thiếu key; cần bảo đảm UI/API
   hiển thị provider và dùng Google Scholar mặc định khi có SerpApi key.
2. Search hiện lưu bài với trạng thái Scopus ban đầu; cần gọi cross-check trong cùng pipeline
   trước response/render, đồng thời trả đủ ba counters.
3. Frontend đang trigger quality-check khi user chọn paper và vẫn có tab Quality riêng; cần gộp
   Search + Verify, giữ Quality tab chỉ như màn re-check/detail.
4. Limit search hiện đang hard-code `10` ở route; cần đổi thành Top 20 cố định hoặc
   constant cấu hình mặc định `GOOGLE_SCHOLAR_TOP_N=20`.
5. Cần bổ sung schema/DB fields cho provider, source rank và counters nếu chưa có migration.
6. `UploadTab`/workspace đã có chunking, nhưng cần kiểm tra quyền theo project, trạng thái độc lập
   và hiển thị page/offset khi mở citation.
7. Export hiện mới là placeholder; synthesis/integrity/retraction và CSL chưa hoàn thiện.
8. Cần test integration cho Google Scholar → Scopus, thiếu ISSN = undetermined, giữ thứ tự,
   dedup và Top 20.

## 7. NFR và acceptance criteria

- Không hiển thị số do AI tự đoán; counters phải truy được về provider/DB.
- Mỗi request external API có timeout, retry hữu hạn, log provider và không lộ API key.
- Không match Scopus do thiếu ISSN không được tự gán `not_indexed`.
- Search lại cùng DOI không tạo duplicate trong một project và không đổi thứ tự GS.
- Search trả tối đa đúng Top 20; kết quả sau lọc có `total_found` và `total_confirmed` đúng.
- Bulk quá 50 trả HTTP 400 rõ giới hạn; screening history không bị ghi đè.
- Upload trước khi extract; gọi extract khi chưa có PDF trả HTTP 409.
- PDF chỉ truy cập trong project; file quá 20 MB bị từ chối.
- LLM JSON lỗi được retry một lần; vẫn lỗi thì trả trạng thái thiếu dữ liệu, không bịa output.

## 8. Roadmap triển khai

**P0:** chuẩn hóa Search & Verify GS→Scopus, Top 20, counters, history, dedup, UI module
gộp; hoàn thiện Screening và Library upload/chunk.

**P1:** ba trạng thái quality đầy đủ, Crossref retraction/integrity, citation verification,
Synthesis có provenance, CSL export, reasoning/progress panel.

**P2:** gap map, ontology theo domain, draft feedback, living review scheduler, Zotero và
collaboration.

## 9. Checklist nghiệm thu P0

- [ ] Có SerpApi key: provider = Google Scholar, thứ tự kết quả được giữ nguyên.
- [ ] Search Google Scholar lấy Top 20 và không vượt limit.
- [ ] Search đối chiếu Scopus trước khi render; có total_found/confirmed/undetermined.
- [ ] Thiếu ISSN không bị gán Not indexed.
- [ ] Search history có query, provider, limit, counters, thời gian và duplicate.
- [ ] Search lặp lại không tạo paper trùng theo DOI/title-author-year.
- [ ] Search & Verify là một navigation; Quality chỉ là re-check/detail.
- [ ] Screening abstract thiếu dữ liệu trả insufficient_info, bulk >50 bị chặn.
- [ ] PDF chunk có page/offset; Library phân biệt pdf và extraction.
- [ ] Mọi lỗi provider/LLM hiển thị message thân thiện và có log kỹ thuật.
