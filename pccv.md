# PCCV — Checklist phân công công việc T165 MVP

## Mục tiêu P0

Hoàn thiện flow chính:

`Research Setup → Search & Verify Top 20 Google Scholar → Scopus cross-check → Screening → Library & Reader → Synthesis MVP → Export`

Nguyên tắc quan trọng: lấy Top 20 từ Google Scholar, giữ thứ tự Google Scholar, sau đó đối chiếu với Scopus. Scopus dùng để xác minh/index badge, không dùng để thay thuật toán tìm kiếm/ranking.

## Checklist đã có trong repo

| Hạng mục | Trạng thái | Ghi chú code |
|---|---|---|
| FastAPI backend base | Đã có | `src/main.py`, `src/api/routes.py` |
| Database models cơ bản | Đã có | `src/models/db_models.py` |
| Project setup API | Đã có | `src/api/project_routes.py` |
| Keyword/search strategy suggestion | Đã có nền | `src/services/search_service.py` gọi LLM và SerpApi count |
| Google Scholar qua SerpApi | Đã có nền | `src/services/scholar_api.py` có `search_papers_serpapi` |
| OpenAlex/Semantic Scholar enrichment/fallback | Đã có nền | `src/services/scholar_api.py` |
| Scopus matcher | Đã có nền tốt | `src/services/scopus_matcher.py` normalize ISSN, match source, coverage |
| Search API | Đã refactor theo P0 nền | `src/api/routes.py` đã dùng Top 20 và chạy Scopus cross-check trong pipeline search |
| Search history/duplicate | Đã có nền | `/search-history`, `/duplicate` |
| Quality check API | Đã có | `/papers/{paper_id}/quality-check`, nên dùng làm re-check/detail |
| Screening API/service | Đã có nền | `screening_routes.py`, `screening_service.py`, bulk max 50 |
| PDF upload/chunking | Đã có nền | `document_processor.py`, `/workspace/upload` |
| Vector search/chat workspace | Đã có nền | `vector_store.py`, `rag_service.py`, `/workspace/chat` |
| Frontend navigation nhiều tab | Đã refactor nền | `Navbar.jsx`, `App.jsx` đã bỏ Quality navigation, đổi Search & Verify, Library & Reader |
| Search UI | Đã refactor nền | `SearchTab.jsx`, `PaperTable.jsx`, `SearchHistoryPanel.jsx` |
| Screening UI | Đã có nền | `ScreeningTab.jsx` |
| Quality UI riêng | Đã loại khỏi navigation chính | `QualityCheckTab.jsx` còn có thể tái dùng làm re-check/detail nếu cần |
| Library/upload UI | Đã có nền | `UploadTab.jsx` |
| Synthesis/workspace UI | Đã có nền | `WorkspaceTab.jsx`, `ChatPanel.jsx`, `VerificationPanel.jsx` |
| Export UI | Chưa hoàn thiện | mới là placeholder trong `App.jsx` |
| Tests | Có nền | `tests/test_api/test_routes.py`, `tests/test_agents/test_graph.py` |

## Checklist việc cần làm tiếp

### P0.1 — Search & Verify backend

- [x] Đổi search mặc định thành Top 20 cố định.
- [x] Bỏ hard-code `limit=10` trong `src/api/routes.py`.
- [x] Đảm bảo khi có SerpApi key thì provider chính là Google Scholar trong route search.
- [x] Search response trả `provider=google_scholar`, `limit=20`.
- [x] Preserve thứ tự `organic_results` từ Google Scholar ở response mặc định.
- [x] Chạy Scopus cross-check trong cùng pipeline search trước khi trả response.
- [x] Trả counters runtime: `total_found`, `total_confirmed`, `total_undetermined`, `duplicates`.
- [x] Không gán thiếu ISSN thành `not_indexed`; dùng `undetermined`.
- [ ] Lưu provider, limit và counters vào DB bằng migration mới.
- [ ] Test integration: Google Scholar Top 20 → Scopus matcher → response.

### P0.2 — Search & Verify frontend

- [x] Đổi label `Search Papers` thành `Search & Verify`.
- [x] Bỏ Quality Check khỏi navigation chính.
- [x] Hiển thị summary cards: provider, found/top20, confirmed, undetermined.
- [x] Gộp badge Scopus/Coverage vào card/table search result hiện có.
- [x] Gộp history panel vào cùng màn Search & Verify.
- [x] Default view ưu tiên bài Scopus confirmed.
- [x] Có filter để xem undetermined.
- [ ] Re-check Scopus đặt trong row action/detail panel.
- [ ] Hiển thị duplicate counter/card chi tiết hơn trong Search & Verify.
- [ ] Chuẩn hóa empty/loading/error copy theo provider fallback.

### P0.3 — Screening

- [ ] Kiểm tra abstract ngắn trả `insufficient_info`.
- [ ] Không hiển thị confidence phần trăm nếu không có metric thật.
- [ ] Bulk decision vẫn chặn trên 50 bài/request.
- [ ] Decision history append-only, không ghi đè.
- [ ] UI cho lý do match/mismatch rõ, dễ scan.

### P0.4 — Library & Reader

- [x] Đổi navigation `Library` thành `Library & Reader`.
- [x] Gộp upload PDF vào Library & Reader ở navigation.
- [ ] Filter theo Scopus status, screening decision, PDF status, extraction status.
- [ ] Giới hạn upload 20 MB/file.
- [ ] File upload scoped theo project.
- [ ] Chunk có page number và char offsets.
- [ ] Reader mở được snippet/provenance khi click citation.
- [ ] Tách rõ `pdf_status` và `extraction_status`.

### P0.5 — Synthesis MVP

- [ ] Chỉ dùng bài đã Keep/extracted.
- [ ] Chat trả lời từ tài liệu đã ingest.
- [ ] Draft/summary có citation gắn chunk.
- [ ] Claim không có evidence bị loại hoặc đánh dấu cần kiểm tra.
- [ ] Citation panel click được về snippet/trang nguồn.

### P0.6 — Export MVP

- [ ] Export CSV metadata.
- [ ] Export BibTeX.
- [ ] Export Markdown summary/citation list.
- [ ] Không ghi đè export cũ.
- [ ] UI hiển thị trạng thái export thành công/thất bại.

## Phân công 2 nhóm làm tiếp

### Nhóm 1 — Search, Verify, Screening, QA backend

Nhóm này phụ trách phần lõi dữ liệu và độ đúng của pipeline. Mục tiêu là đảm bảo kết quả user thấy thật sự là Top 20 Google Scholar đã được đối chiếu Scopus, có trạng thái rõ, có test và không bịa dữ liệu.

Phạm vi chính:

- `src/api/routes.py`
- `src/models/schemas.py`
- `src/models/search_schemas.py`
- `src/models/db_models.py`
- `src/services/scholar_api.py`
- `src/services/scopus_matcher.py`
- `src/api/screening_routes.py`
- `src/services/screening_service.py`
- `tests/test_api/*`

Việc cần làm tiếp:

- [ ] Thêm migration/schema cho `search_queries`: `provider`, `requested_limit`, `total_found`, `total_confirmed`, `total_undetermined`, `duplicates`.
- [ ] Cập nhật model `SearchQuery` và response history để đọc được các counters đã lưu.
- [ ] Viết test cho Search & Verify: Top 20, giữ thứ tự Google Scholar, Scopus indexed, thiếu ISSN = `undetermined`, duplicate trong project.
- [ ] Mock SerpApi/Google Scholar trong test để không phụ thuộc quota/API key.
- [ ] Kiểm tra performance Scopus check; nếu chậm thì tối ưu batch match theo ISSN/title thay vì gọi tuần tự từng paper.
- [ ] Hoàn thiện fallback provider: thiếu/quota SerpApi thì response phải ghi rõ fallback, không gắn nhãn Google Scholar.
- [ ] Screening: abstract ngắn trả `insufficient_info`, không gọi LLM.
- [ ] Screening: không hiển thị confidence phần trăm nếu không có metric thật.
- [ ] Screening: bảo đảm decision history append-only và bulk >50 trả lỗi rõ.
- [ ] Thêm regression tests cho screening decision/history/bulk.

Deliverable cuối của Nhóm 1:

- API Search & Verify ổn định, có dữ liệu counters lưu DB.
- Search history phản ánh đúng provider/limit/counters.
- Screening backend có guard và test.
- Test backend pass trong CI/local.

### Nhóm 2 — UI workflow, Library/Reader, Synthesis, Export

Nhóm này phụ trách trải nghiệm user và các màn sau Search. Mục tiêu là biến flow trong `Dashboard.md` thành UI dùng được: ít navigation, nhiều capability tích hợp trong cùng màn, đọc được bài, tổng hợp có nguồn và export được.

Phạm vi chính:

- `frontend/src/App.jsx`
- `frontend/src/components/Navbar.jsx`
- `frontend/src/components/home/HomeTab.jsx`
- `frontend/src/components/search/*`
- `frontend/src/components/screening/ScreeningTab.jsx`
- `frontend/src/components/upload/UploadTab.jsx`
- `frontend/src/components/workspace/*`
- `frontend/src/components/insights/InsightsTab.jsx`
- `frontend/src/utils/excelExport.js`
- `src/services/document_processor.py`
- `src/services/vector_store.py`
- `src/services/rag_service.py`
- `src/agents/graph.py`

Việc cần làm tiếp:

- [ ] Search & Verify UI: thêm action re-check Scopus trong row/detail panel.
- [ ] Search & Verify UI: hiển thị duplicate counter/card chi tiết hơn.
- [ ] Search & Verify UI: chuẩn hóa empty/loading/error copy theo provider/fallback.
- [ ] Overview: bổ sung counters project: searched, confirmed, undetermined, Keep, PDF uploaded, extracted.
- [ ] Overview: thêm CTA bước tiếp theo theo trạng thái project.
- [ ] Screening UI: hiển thị reason match/mismatch rõ, dễ scan; hỗ trợ note và bulk action mượt.
- [ ] Library & Reader: filter theo Scopus status, screening decision, PDF status, extraction status.
- [ ] Library & Reader: giới hạn upload 20 MB/file ở frontend và backend.
- [ ] Library & Reader: file upload scoped theo project.
- [ ] Library & Reader: chunk có page number và char offsets; reader mở được snippet/provenance.
- [ ] Synthesis: chỉ dùng bài đã Keep/extracted.
- [ ] Synthesis: chat trả lời closed-domain từ tài liệu đã ingest.
- [ ] Synthesis: draft/summary có citation gắn chunk; claim không evidence phải bị loại hoặc đánh dấu cần kiểm tra.
- [ ] Export: implement CSV, BibTeX, Markdown summary/citation list.
- [ ] Export: không ghi đè bản export cũ; UI có trạng thái export thành công/thất bại.

Deliverable cuối của Nhóm 2:

- UI đúng 7 navigation trong `Dashboard.md`.
- Search & Verify/Screening/Library/Synthesis chạy thành flow liền mạch.
- Reader và Synthesis có provenance/citation.
- Export MVP dùng được.

## Ranh giới phối hợp giữa 2 nhóm

- Nhóm 1 chốt contract API cho Search & Verify trước, Nhóm 2 có thể dùng mock JSON để làm UI trong lúc chờ migration.
- Nhóm 1 chịu trách nhiệm dữ liệu đúng; Nhóm 2 chịu trách nhiệm hiển thị đúng và không làm user hiểu nhầm.
- Nhóm 2 cần báo sớm nếu UI cần thêm field trong response, ví dụ `source_rank`, `match_reason`, `scopus_source_title`.
- Hai nhóm cùng thống nhất format status: `indexed`, `undetermined`, `out_of_coverage`, `not_applicable`; không tự tạo status mới ở frontend.
- QA cuối nên chạy chung: một search Top 20 thật/mocked, filter confirmed, đưa bài sang Screening, Keep, upload PDF, hỏi Synthesis, export metadata.

## Thứ tự ghép việc khuyến nghị

1. Chốt contract Search & Verify response.
2. Backend Search & Verify Top 20 + Scopus cross-check.
3. Frontend Search & Verify gộp Quality.
4. Screening quyết định Keep/Remove/Maybe.
5. Library & Reader upload/chunk/provenance.
6. Synthesis dùng chunks có citation.
7. Export metadata và markdown.
8. QA integration end-to-end.

## Rủi ro cần để ý

- SerpApi quota hoặc thiếu key: UI phải ghi rõ fallback, không gọi fallback là Google Scholar.
- Scopus source list không có quartile đáng tin: không bịa Q1/Q2 nếu không có dataset CiteScore.
- Không match vì thiếu ISSN không có nghĩa là không Scopus.
- Search response sau khi lọc confirmed có thể ít hơn 20; vẫn phải giữ `total_found=20`.
- LLM chỉ hỗ trợ, không tạo counters hay quyết định thay user.
