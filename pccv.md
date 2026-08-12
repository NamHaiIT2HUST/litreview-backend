# PCCV — Checklist hoàn thiện MVP Phase 1 dự án T165

## 1. Mục tiêu Phase 1 MVP

Hoàn thiện một flow demo/đánh giá được từ đầu đến cuối:

`Research Setup → Search & Verify Top 20 Google Scholar → Scopus Cross-check → Screening → Library & Reader → Synthesis có citation → Export`

Nguyên tắc sản phẩm:

- Google Scholar là nguồn tìm kiếm chính trong MVP.
- Backend lấy Top 20 từ Google Scholar và giữ đúng thứ tự Google Scholar trả về.
- Scopus chỉ dùng để đối chiếu/index badge, không dùng để thay ranking của Google Scholar.
- Không match Scopus do thiếu DOI/ISSN/metadata thì hiển thị `undetermined`, không được gọi là `not_indexed`.
- Mọi số đếm/counter phải lấy từ provider hoặc DB thật, không để LLM tự ước lượng.
- UI không cần mỗi module là một tab riêng. Những chức năng nào user dùng liền nhau thì gộp trong cùng navigation.

Navigation Phase 1:

`Overview → Research Setup → Search & Verify → Screening → Library & Reader → Synthesis → Export`

## 2. Tình trạng nền hiện có trong repo

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| FastAPI backend | Đã có nền | `src/main.py`, `src/api/routes.py` |
| Project setup API | Đã có nền | `src/api/project_routes.py` |
| DB models | Đã có nền | `src/models/db_models.py` |
| Google Scholar/SerpApi service | Đã có nền | `src/services/scholar_api.py` |
| OpenAlex/Semantic Scholar fallback/enrichment | Đã có nền | `src/services/scholar_api.py` |
| Scopus matcher | Đã có nền tốt | `src/services/scopus_matcher.py` |
| Search API/history/duplicate | Đã có nền | `src/api/routes.py` |
| Screening API/service | Đã có nền | `src/api/screening_routes.py`, `src/services/screening_service.py` |
| PDF upload/chunking | Đã có nền | `src/services/document_processor.py`, `/workspace/upload` |
| Vector search/RAG workspace | Đã có nền | `src/services/vector_store.py`, `src/services/rag_service.py` |
| Synthesis/evidence-first backend | Có nền từ main | `src/services/synthesis_service.py`, `src/synthesis/graph.py` |
| Frontend navigation | Có nền | `frontend/src/App.jsx`, `Navbar.jsx` |
| Search UI | Có nền | `frontend/src/components/search/*` |
| Screening UI | Có nền | `frontend/src/components/screening/ScreeningTab.jsx` |
| Library/upload UI | Có nền | `frontend/src/components/upload/UploadTab.jsx` |
| Workspace/Synthesis UI | Có nền | `frontend/src/components/workspace/*` |
| Export UI | Chưa hoàn thiện | còn placeholder/chưa đủ flow |
| Tests | Có nền | `tests/*`, nhưng cần bổ sung integration tests |

## 3. Checklist chi tiết còn cần làm

### 3.1 Overview Dashboard

Mục tiêu: user mở project lên là biết đang ở bước nào và nên làm gì tiếp theo.

Backend/API:

- [ ] Có endpoint hoặc cơ chế aggregate project summary.
- [ ] Tính được tổng số paper đã search trong project.
- [ ] Tính được số paper Scopus confirmed.
- [ ] Tính được số paper `undetermined`.
- [ ] Tính được số paper đã Keep/Remove/Maybe.
- [ ] Tính được số paper đã upload PDF.
- [ ] Tính được số paper đã extraction/chunking xong.
- [ ] Tính được synthesis session gần nhất và trạng thái.

Frontend:

- [ ] Overview hiển thị project name/research question hiện tại.
- [ ] Có cards: searched, confirmed, undetermined, Keep, PDF uploaded, extracted.
- [ ] Có recent activity: search gần nhất, screening gần nhất, upload gần nhất, synthesis gần nhất.
- [ ] Có CTA theo trạng thái:
  - [ ] Chưa có setup → đi Research Setup.
  - [ ] Đã setup → đi Search & Verify.
  - [ ] Có search result → đi Screening.
  - [ ] Có Keep → đi Library & Reader.
  - [ ] Có extracted paper → đi Synthesis.
  - [ ] Có draft/synthesis result → đi Export.

Acceptance criteria:

- [ ] User nhìn Overview hiểu project đang thiếu bước nào.
- [ ] Counter không hard-code, không do LLM sinh.
- [ ] Empty state rõ ràng khi chưa có project/search/paper.

### 3.2 Research Setup

Mục tiêu: tạo context nghiên cứu đủ dùng cho search và screening.

Backend/API:

- [ ] Kiểm tra Project CRUD end-to-end.
- [ ] Validate required fields: project name, research question, research field.
- [ ] Validate year range nếu có.
- [ ] Lưu inclusion/exclusion criteria dạng list rõ ràng.
- [ ] API update criteria không làm mất dữ liệu cũ ngoài ý muốn.
- [ ] Query/keyword suggestion trả JSON hợp lệ.
- [ ] Nếu LLM trả JSON lỗi thì fallback hoặc báo lỗi thân thiện.

Frontend:

- [ ] Form nhập project name, research question, field, year range.
- [ ] UI nhập inclusion/exclusion criteria dễ dùng.
- [ ] Hiển thị cảnh báo nếu thiếu criteria: screening sẽ kém chính xác hơn.
- [ ] Có nút sinh query/keyword suggestion.
- [ ] Có nút dùng query suggestion để chuyển sang Search & Verify.
- [ ] Loading/error state cho query suggestion.

Acceptance criteria:

- [ ] Tạo/sửa project không lỗi.
- [ ] Criteria được lưu và dùng lại ở Screening.
- [ ] Query suggestion không làm app crash khi LLM lỗi.

### 3.3 Search & Verify — Backend

Mục tiêu: lấy Top 20 Google Scholar, đối chiếu Scopus ngay, trả kết quả minh bạch.

Search provider:

- [x] Lấy Top 20 cố định theo spec.
- [x] Preserve thứ tự Google Scholar organic results.
- [ ] Đảm bảo khi có SerpApi key thì provider chính là Google Scholar.
- [ ] Khi thiếu/quota SerpApi thì fallback rõ ràng, không gắn nhãn Google Scholar.
- [ ] Timeout/retry external API có giới hạn.
- [ ] Log provider, query, latency, lỗi; không log API key.

Metadata/enrichment:

- [ ] Bổ sung DOI nếu Google Scholar thiếu.
- [ ] Bổ sung abstract nếu thiếu.
- [ ] Bổ sung ISSN/EISSN nếu có thể.
- [ ] Lưu `source_rank` theo thứ tự Google Scholar.
- [ ] Không đổi ranking sau enrichment.

Dedup:

- [ ] Dedup theo DOI normalized.
- [ ] Fallback dedup theo `title_norm|first_author|year`.
- [ ] Dedup scoped theo project.
- [ ] Search lặp lại không tạo paper trùng.
- [ ] Paper duplicate vẫn trả canonical DB id để frontend dùng.

Scopus cross-check:

- [x] Có service normalize ISSN và match Scopus.
- [ ] Match theo ISSN.
- [ ] Match theo EISSN.
- [ ] Fallback title match nếu dữ liệu đủ tin cậy.
- [ ] Coverage-year check theo coverage ranges.
- [ ] Thiếu ISSN/DOI/title không đủ match → `undetermined`.
- [ ] Không tự gán `not_indexed` nếu không có nguồn xác nhận.
- [ ] Nếu performance chậm, tối ưu batch match thay vì check từng paper tuần tự.

Search response:

- [x] Trả `provider`.
- [x] Trả `limit=20`.
- [x] Trả `total_found`, `total_confirmed`, `total_undetermined`, `duplicates` ở runtime.
- [ ] Trả `source_rank`.
- [ ] Trả `scopus_source_title` nếu match được.
- [ ] Trả `match_reason` hoặc `match_method`: `issn`, `eissn`, `title`, `none`.
- [ ] Trả error/fallback message thân thiện.

DB/migration:

- [ ] Thêm migration cho `search_queries.provider`.
- [ ] Thêm migration cho `search_queries.requested_limit`.
- [ ] Thêm migration cho `search_queries.total_found`.
- [ ] Thêm migration cho `search_queries.total_confirmed`.
- [ ] Thêm migration cho `search_queries.total_undetermined`.
- [ ] Thêm migration cho `search_queries.duplicates`.
- [ ] Thêm/kiểm tra `papers.source_rank`.
- [ ] Thêm/kiểm tra `papers.scopus_status`.
- [ ] Thêm/kiểm tra `papers.coverage_year_status`.
- [ ] Thêm/kiểm tra `papers.dedup_key`.
- [ ] Search history đọc lại được provider/limit/counters đã lưu.

Tests:

- [ ] Mock SerpApi trả đúng 20 paper.
- [ ] Test giữ thứ tự Google Scholar.
- [ ] Test match ISSN → `indexed`.
- [ ] Test match EISSN → `indexed`.
- [ ] Test out-of-coverage.
- [ ] Test thiếu ISSN → `undetermined`.
- [ ] Test duplicate trong cùng project.
- [ ] Test fallback provider không bị ghi nhãn Google Scholar.
- [ ] Test response counters đúng.

Acceptance criteria:

- [ ] Search thật/mocked trả tối đa đúng Top 20.
- [ ] UI/API show được kết quả đã Scopus cross-check trước khi user screening.
- [ ] Không có status sai kiểu thiếu dữ liệu mà gọi là không indexed.

### 3.4 Search & Verify — Frontend

Mục tiêu: một màn search có đủ tìm kiếm, verify, history, filter; không bắt user sang tab Quality riêng.

UI chính:

- [x] Navigation dùng label `Search & Verify`.
- [x] Quality Check không còn là navigation chính.
- [ ] Search bar nhập query.
- [ ] Query strategy chips từ Research Setup.
- [ ] Provider banner: Google Scholar hoặc Fallback.
- [ ] Summary cards:
  - [ ] Provider.
  - [ ] Found/Top 20.
  - [ ] Scopus confirmed.
  - [ ] Undetermined.
  - [ ] Duplicates.
- [ ] Table/card result giữ thứ tự Google Scholar.
- [ ] Hiển thị `source_rank`.
- [ ] Badge Scopus status.
- [ ] Badge coverage-year status.
- [ ] Badge OA status nếu có.
- [ ] Abstract modal/detail drawer.
- [ ] Source link/DOI link.

Filter/action:

- [ ] Default ưu tiên hoặc filter nhanh Scopus confirmed.
- [ ] Có filter xem `undetermined`.
- [ ] Có filter theo year/journal nếu có dữ liệu.
- [ ] Add to Screening/Library.
- [ ] Row action re-check Scopus.
- [ ] Duplicate query từ history.
- [ ] Không có selector Top 10/20 trong MVP nếu spec chốt Top 20.

State/copy:

- [ ] Loading copy: đang gọi Google Scholar.
- [ ] Empty copy: chưa có kết quả.
- [ ] Fallback copy: đang dùng provider khác vì thiếu/quota SerpApi.
- [ ] Error copy: timeout/quota/key lỗi.
- [ ] Không show stacktrace cho user.

Acceptance criteria:

- [ ] User search một lần là thấy kết quả Top 20 đã verify.
- [ ] User hiểu rõ bài nào confirmed, bài nào undetermined.
- [ ] History nằm trong cùng workflow, không phải navigation riêng.

### 3.5 Screening

Mục tiêu: giúp user quyết định Keep/Remove/Maybe theo criteria, có lý do rõ.

Backend:

- [ ] Abstract dưới ngưỡng cấu hình trả `insufficient_info`.
- [ ] Abstract thiếu/empty không gọi LLM.
- [ ] LLM nhận research question + criteria + abstract, không nhận dữ liệu thừa.
- [ ] Parse JSON LLM an toàn.
- [ ] LLM lỗi thì trả trạng thái thiếu dữ liệu, không bịa output.
- [ ] Không tạo confidence percentage nếu không có metric thật.
- [ ] Bulk decision giới hạn tối đa 50 paper/request.
- [ ] Bulk >50 trả HTTP 400 với message rõ.
- [ ] Decision history append-only.
- [ ] Đổi decision không xóa lịch sử cũ.
- [ ] Priority recompute nếu còn dùng priority score.

Frontend:

- [ ] Bảng bài chờ screening.
- [ ] Hiển thị relevance bucket: High/Medium/Low/Insufficient info.
- [ ] Hiển thị reason matches/mismatches rõ, dễ scan.
- [ ] Decision buttons: Keep/Remove/Maybe.
- [ ] User note cho từng decision.
- [ ] Bulk Keep/Remove/Maybe.
- [ ] Filter theo relevance bucket.
- [ ] Filter theo decision.
- [ ] Filter theo Scopus status.
- [ ] History decision hoặc last decision hiển thị rõ.

Tests:

- [ ] Test abstract ngắn.
- [ ] Test LLM mocked trả JSON hợp lệ.
- [ ] Test LLM malformed JSON.
- [ ] Test decision append-only.
- [ ] Test bulk <=50.
- [ ] Test bulk >50.

Acceptance criteria:

- [ ] User có thể chọn Keep/Remove/Maybe và xem lý do.
- [ ] Không có confidence giả.
- [ ] History không bị ghi đè.

### 3.6 Library & Reader

Mục tiêu: quản lý bài đã Keep, upload PDF hợp pháp, đọc sâu và tạo provenance cho synthesis.

Backend:

- [ ] Library scoped theo project.
- [ ] Chỉ bài Keep mới mặc định vào Library chính.
- [ ] Upload PDF scoped theo project và paper.
- [ ] Giới hạn upload 20 MB/file ở backend.
- [ ] Check file type PDF.
- [ ] Không lưu file ở public path.
- [ ] Tách rõ `pdf_status` và `extraction_status`.
- [ ] `pdf_status`: `not_uploaded`, `user_uploaded`, `oa_auto_fetched` nếu có.
- [ ] `extraction_status`: `not_extracted`, `extracted`, `failed`.
- [ ] Parse PDF theo page.
- [ ] Chunk lưu `page_number`.
- [ ] Chunk lưu `char_start`.
- [ ] Chunk lưu `char_end`.
- [ ] Chunk lưu `paper_id`.
- [ ] Chunk lưu `ingestion_id`.
- [ ] Vector store lưu metadata đủ để trace citation.
- [ ] Re-upload PDF tạo ingestion version mới, không làm citation cũ mập mờ.
- [ ] Cleanup vector cũ an toàn sau DB commit.

Frontend:

- [ ] Navigation `Library & Reader`.
- [ ] Danh sách paper Keep.
- [ ] Filter theo Scopus status.
- [ ] Filter theo screening decision.
- [ ] Filter theo PDF status.
- [ ] Filter theo extraction status.
- [ ] Upload PDF ở từng paper.
- [ ] Giới hạn 20 MB ở frontend.
- [ ] Reader 2-pane:
  - [ ] Pane trái: PDF/text/snippet.
  - [ ] Pane phải: metadata/note/citation/provenance.
- [ ] Click citation/snippet mở đúng page/source.
- [ ] Upload/extraction loading state.
- [ ] Upload/extraction error state.

Tests:

- [ ] Test upload file quá 20 MB.
- [ ] Test upload non-PDF.
- [ ] Test upload đúng project.
- [ ] Test parse page number.
- [ ] Test chunk offsets reconstruct được text.
- [ ] Test vector metadata có paper/page/offset.

Acceptance criteria:

- [ ] User upload PDF cho paper Keep được.
- [ ] Hệ thống extract/chunk có provenance.
- [ ] Reader mở được snippet/trang nguồn khi citation gọi tới.

### 3.7 Synthesis MVP

Mục tiêu: tổng hợp từ các paper đã Keep/extracted, có citation traceable, không viết tự do không nguồn.

Backend:

- [ ] Chỉ cho chọn paper đã Keep.
- [ ] Chỉ cho chọn paper đã extracted.
- [ ] Giới hạn số paper synthesis, khuyến nghị tối đa 15.
- [ ] Tạo synthesis session.
- [ ] Session status: `processing`, `done`, `failed`.
- [ ] Retrieve chunks theo selected papers/project.
- [ ] Closed-domain chat chỉ dùng chunks đã ingest.
- [ ] Nếu không có chunk đủ bằng chứng thì trả “không tìm thấy trong tài liệu”.
- [ ] Draft/summary mỗi claim/câu phải có citation.
- [ ] Claim không có evidence bị loại hoặc đánh dấu cần kiểm tra.
- [ ] Citation lưu được paper/page/chunk/offset.
- [ ] Error LLM được xử lý không làm mất session.
- [ ] Không gọi một prompt lớn cho toàn bộ review không provenance.

Frontend:

- [ ] Màn chọn paper đã Keep/extracted.
- [ ] Hiển thị số paper đã chọn và giới hạn.
- [ ] Start synthesis button.
- [ ] Hiển thị progress/status.
- [ ] Hiển thị outline nếu có.
- [ ] Hiển thị draft/summary.
- [ ] Citation panel.
- [ ] Click citation mở Reader/snippet.
- [ ] Chat closed-domain trên selected papers.
- [ ] Empty state khi chưa có extracted paper.

Tests:

- [ ] Test không cho synthesis paper chưa Keep.
- [ ] Test không cho synthesis paper chưa extracted.
- [ ] Test retrieve scoped theo selected papers.
- [ ] Test draft có citation.
- [ ] Test citation trace về chunk/page.
- [ ] Test LLM mocked lỗi.

Acceptance criteria:

- [ ] User tạo được synthesis từ bài đã ingest.
- [ ] Mỗi claim/câu quan trọng có citation.
- [ ] Citation click được về nguồn.

### 3.8 Export MVP

Mục tiêu: user lấy kết quả ra ngoài dùng tiếp.

Định dạng MVP:

- [ ] CSV metadata.
- [ ] BibTeX.
- [ ] Markdown summary/citation list.

CSV fields tối thiểu:

- [ ] title.
- [ ] authors.
- [ ] year.
- [ ] journal.
- [ ] DOI.
- [ ] ISSN/EISSN.
- [ ] URL/source.
- [ ] Google Scholar rank/source_rank.
- [ ] Scopus status.
- [ ] Coverage status.
- [ ] Screening decision.
- [ ] PDF status.
- [ ] Extraction status.

BibTeX:

- [ ] Generate key ổn định.
- [ ] Escape ký tự đặc biệt.
- [ ] Có title/authors/year/journal/doi/url nếu có.
- [ ] Không bịa field thiếu.

Markdown:

- [ ] Export search summary.
- [ ] Export selected papers.
- [ ] Export synthesis draft nếu có.
- [ ] Export citation list/provenance.

Storage/UI:

- [ ] Không ghi đè export cũ.
- [ ] Có timestamp/version cho export.
- [ ] UI hiển thị export success.
- [ ] UI hiển thị export failed.
- [ ] Có nút download.

Tests:

- [ ] Test CSV headers.
- [ ] Test BibTeX escape.
- [ ] Test Markdown có citation.
- [ ] Test export không ghi đè file cũ.

Acceptance criteria:

- [ ] User export được CSV/BibTeX/Markdown.
- [ ] File xuất ra dùng được, không chứa dữ liệu bịa.

## 4. Data model/migration cần rà soát

Các field/table cần có hoặc cần kiểm tra lại trước khi chốt Phase 1:

### Projects

- [ ] `id`
- [ ] `name`
- [ ] `research_question`
- [ ] `research_field`
- [ ] `year_from`
- [ ] `year_to`
- [ ] `criteria_include`
- [ ] `criteria_exclude`

### Search queries

- [ ] `id`
- [ ] `project_id`
- [ ] `query_string`
- [ ] `strategy_label`
- [ ] `provider`
- [ ] `requested_limit`
- [ ] `total_found`
- [ ] `total_confirmed`
- [ ] `total_undetermined`
- [ ] `duplicates`
- [ ] `executed_at`
- [ ] `is_duplicated_from`

### Papers

- [ ] `id`
- [ ] `project_id`
- [ ] `search_query_id`
- [ ] `source_rank`
- [ ] `title`
- [ ] `authors`
- [ ] `year`
- [ ] `abstract`
- [ ] `journal`
- [ ] `doi`
- [ ] `issn`
- [ ] `eissn`
- [ ] `url`
- [ ] `dedup_key`
- [ ] `scopus_status`
- [ ] `scopus_source_title`
- [ ] `scopus_match_method`
- [ ] `coverage_year_status`
- [ ] `oa_status`
- [ ] `screening_decision`
- [ ] `pdf_status`
- [ ] `extraction_status`
- [ ] `active_ingestion_id`

### Screening history

- [ ] `id`
- [ ] `paper_id`
- [ ] `decision`
- [ ] `ai_reason`
- [ ] `user_note`
- [ ] `decided_at`
- [ ] `decided_by` nếu cần.

### PDF/page/chunk/provenance

- [ ] `ingestion_id`
- [ ] `paper_id`
- [ ] `page_number`
- [ ] `char_start`
- [ ] `char_end`
- [ ] `text`
- [ ] `vector_id`
- [ ] `created_at`

### Synthesis/citation

- [ ] `synthesis_sessions`
- [ ] `evidence_records`
- [ ] `synthesis_claims`
- [ ] `claim_evidence_links`
- [ ] `citations`
- [ ] status/progress/error fields.

## 5. Phân công 2 nhóm

### Nhóm 1 — Backend Search/Verify/Screening/QA

Phạm vi:

- `src/api/routes.py`
- `src/api/project_routes.py`
- `src/api/screening_routes.py`
- `src/models/db_models.py`
- `src/models/schemas.py`
- `src/models/search_schemas.py`
- `src/models/screening_schemas.py`
- `src/services/scholar_api.py`
- `src/services/scopus_matcher.py`
- `src/services/search_service.py`
- `src/services/screening_service.py`
- `alembic/*`
- `tests/*`

Đầu việc:

- [ ] Chốt Search & Verify API contract.
- [ ] Thêm migration SearchQuery counters/provider/limit.
- [ ] Thêm/kiểm tra `source_rank`, Scopus match metadata ở Paper.
- [ ] Hoàn thiện Google Scholar Top 20 + provider fallback.
- [ ] Hoàn thiện Scopus cross-check và batch performance.
- [ ] Hoàn thiện search history counters.
- [ ] Hoàn thiện duplicate handling.
- [ ] Hoàn thiện screening guard/history/bulk.
- [ ] Mock external APIs trong tests.
- [ ] Bảo đảm CI/local tests không cần API key thật.

Deliverable:

- [ ] Search & Verify backend chạy ổn.
- [ ] Search history phản ánh đúng dữ liệu.
- [ ] Screening backend đủ guard.
- [ ] Backend tests pass.

### Nhóm 2 — Frontend Workflow/Library/Synthesis/Export

Phạm vi:

- `frontend/src/App.jsx`
- `frontend/src/components/Navbar.jsx`
- `frontend/src/components/home/HomeTab.jsx`
- `frontend/src/components/research/*`
- `frontend/src/components/search/*`
- `frontend/src/components/screening/*`
- `frontend/src/components/upload/*`
- `frontend/src/components/workspace/*`
- `frontend/src/components/insights/*`
- `frontend/src/utils/*`
- `src/services/document_processor.py`
- `src/services/vector_store.py`
- `src/services/rag_service.py`
- `src/services/synthesis_service.py`
- `src/synthesis/graph.py`

Đầu việc:

- [ ] Hoàn thiện Overview dashboard.
- [ ] Hoàn thiện Research Setup UX.
- [ ] Hoàn thiện Search & Verify UI gộp Quality.
- [ ] Hoàn thiện Screening UX.
- [ ] Hoàn thiện Library & Reader.
- [ ] Hoàn thiện upload/chunk/provenance hiển thị được.
- [ ] Hoàn thiện Synthesis UI có citation panel.
- [ ] Hoàn thiện Export CSV/BibTeX/Markdown.
- [ ] Chuẩn hóa loading/empty/error copy toàn app.

Deliverable:

- [ ] UI đúng 7 navigation.
- [ ] User đi được flow end-to-end.
- [ ] Citation/provenance xem được.
- [ ] Export dùng được.

## 6. Thứ tự ưu tiên triển khai Phase 1

### Sprint A — Chốt lõi Search & Verify

1. [ ] Chốt API contract Search & Verify.
2. [ ] Migration provider/limit/counters/source_rank.
3. [ ] Backend Search Top 20 + Scopus cross-check + history.
4. [ ] Frontend Search & Verify cards/table/filter/history.
5. [ ] Tests Search & Verify mocked.

### Sprint B — Screening + Library foundation

1. [ ] Screening guard/history/bulk.
2. [ ] Screening UI reason/note/bulk.
3. [ ] Library list/filter.
4. [ ] Upload PDF 20 MB + project scope.
5. [ ] Chunk page/offset/provenance.

### Sprint C — Synthesis + Export

1. [ ] Synthesis chỉ dùng Keep/extracted.
2. [ ] Closed-domain chat/draft có citation.
3. [ ] Citation click về Reader/snippet.
4. [ ] Export CSV.
5. [ ] Export BibTeX.
6. [ ] Export Markdown.

### Sprint D — Polish/QA demo

1. [ ] Overview dashboard.
2. [ ] Loading/empty/error copy.
3. [ ] E2E QA flow mocked.
4. [ ] E2E QA flow với key thật nếu có.
5. [ ] README/RUN_GUIDE cập nhật.
6. [ ] Fix CI/GitHub Actions nếu billing/workflow còn lỗi.

## 7. Definition of Done cho MVP Phase 1

MVP Phase 1 được coi là hoàn thiện khi:

- [ ] User tạo project được.
- [ ] User search được Top 20 Google Scholar.
- [ ] Kết quả search giữ đúng thứ tự provider.
- [ ] Mỗi result có trạng thái Scopus rõ: `indexed` hoặc `undetermined`.
- [ ] Search history lưu được provider/limit/counters.
- [ ] Duplicate không tạo paper trùng trong project.
- [ ] User screening Keep/Remove/Maybe được.
- [ ] Screening có reason và history.
- [ ] User upload PDF cho paper Keep được.
- [ ] PDF được parse/chunk có page/offset.
- [ ] User synthesis từ bài đã Keep/extracted được.
- [ ] Draft/chat có citation gắn nguồn.
- [ ] Click citation xem được snippet/page.
- [ ] User export CSV/BibTeX/Markdown được.
- [ ] Không có số liệu do LLM bịa.
- [ ] Tests backend trọng yếu pass.
- [ ] UI không crash ở các empty/error states chính.

## 8. Rủi ro cần kiểm soát

- [ ] SerpApi thiếu key/quota khiến search fallback nhưng UI hiểu nhầm là Google Scholar.
- [ ] Scopus Source Title List không có quartile đáng tin, không được bịa Q1/Q2.
- [ ] Thiếu ISSN bị hiểu nhầm thành không thuộc Scopus.
- [ ] Search filtered confirmed có thể ít hơn 20, nhưng `total_found` vẫn phải là số kết quả provider trả về.
- [ ] LLM trả JSON lỗi làm crash flow.
- [ ] Upload PDF bản quyền/không hợp lệ.
- [ ] Chunk thiếu offset khiến citation không trace được.
- [ ] Vector store và DB lệch ingestion version.
- [ ] CI/GitHub Actions fail do billing hoặc thiếu secrets.
- [ ] Team tự tạo status mới ở frontend không khớp backend.

## 9. QA kịch bản nghiệm thu end-to-end

Kịch bản demo tối thiểu:

1. [ ] Tạo project với research question và criteria.
2. [ ] Sinh query suggestion hoặc nhập query thủ công.
3. [ ] Search & Verify trả Top 20.
4. [ ] UI hiển thị confirmed/undetermined/duplicates.
5. [ ] Mở abstract một paper.
6. [ ] Add một số paper sang Screening.
7. [ ] Screening AI trả reason.
8. [ ] User Keep ít nhất 2 paper.
9. [ ] Upload PDF cho paper Keep.
10. [ ] Extraction/chunking hoàn tất.
11. [ ] Synthesis tạo draft có citation.
12. [ ] Click citation mở snippet/page nguồn.
13. [ ] Export CSV/BibTeX/Markdown.

Nếu một bước dùng mock data thì phải ghi rõ trong demo note, không trình bày như dữ liệu thật.
