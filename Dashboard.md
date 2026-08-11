# Dashboard UI Navigation — T165 MVP

## Nguyên tắc navigation

UI không tách theo từng module kỹ thuật. Một navigation có thể gộp nhiều capability nếu chúng nằm trong cùng một luồng làm việc của user.

MVP ưu tiên ít navigation, thao tác liền mạch:

`Overview → Research Setup → Search & Verify → Screening → Library & Reader → Synthesis → Export`

Google Scholar là nguồn tìm kiếm chính. Hệ thống lấy Top 20 theo đúng thứ tự Google Scholar trả về, sau đó đối chiếu từng bài với danh mục Scopus và show kết quả đã đối chiếu cho user.

## Navigation đề xuất

| Navigation | Mục đích | Tính năng trong màn | Capability tích hợp | Component hiện có để tận dụng |
|---|---|---|---|---|
| Overview | Cho user nhìn nhanh trạng thái project và bước tiếp theo | project progress, tổng số bài đã search, số bài Scopus confirmed, số bài Keep, PDF uploaded, extraction done, shortcut sang bước tiếp theo | dashboard aggregation, project metrics, recent activity | `HomeTab.jsx`, một phần `StatCards.jsx` |
| Research Setup | Khởi tạo/ngữ cảnh hóa đề tài nghiên cứu | project name, research question, research field, year range, inclusion/exclusion criteria, keyword/query suggestion | project CRUD, criteria validation, LLM query suggestion | `ResearchSetupTab.jsx`, `project_routes.py`, `search_service.py` |
| Search & Verify | Màn trọng tâm: tìm Top 20 trên Google Scholar rồi đối chiếu Scopus ngay | search bar, query strategy chips, provider banner, Top 20 result table, Scopus badge, coverage badge, abstract modal, history drawer, duplicate action, add to Screening/Library | Google Scholar search, OpenAlex/S2 enrichment, dedup, Scopus matcher, coverage check, search history | `SearchTab.jsx`, `SearchBar.jsx`, `PaperTable.jsx`, `SearchHistoryPanel.jsx`, `AbstractModal.jsx`, `QualityCheckTab.jsx` nên gộp lại thành re-check/detail |
| Screening | Quyết định bài nào giữ/bỏ theo criteria | AI relevance bucket, reason match/mismatch, decision Keep/Remove/Maybe, note, bulk action, decision history | AI screening, insufficient-info guard, decision persistence, priority recompute | `ScreeningTab.jsx`, `screening_routes.py`, `screening_service.py` |
| Library & Reader | Quản lý bài đã Keep và đọc sâu bằng PDF | saved paper list, filter theo Scopus/screening/PDF/extraction, upload PDF, reader 2 pane, citation/provenance snippet | library management, upload, PDF parsing, chunking, vector indexing, provenance | `UploadTab.jsx`, `WorkspaceTab.jsx`, `document_processor.py`, `vector_store.py` |
| Synthesis | Tổng hợp dựa trên các bài đã ingest | chọn bài đã Keep/extracted, outline, draft, closed-domain chat, citation panel, click citation xem nguồn | RAG retrieval, LangGraph outline/draft, citation traceability, evidence guard | `WorkspaceTab.jsx`, `ChatPanel.jsx`, `VerificationPanel.jsx`, `InsightsTab.jsx`, `rag_service.py`, `agents/graph.py` |
| Export | Xuất kết quả cho user dùng tiếp | export CSV, BibTeX, Markdown summary, citation list, trạng thái export | metadata formatter, citation formatter, file generation | export placeholder trong `App.jsx`, `excelExport.js` |

## Chi tiết từng navigation

### 1. Overview

User cần biết project đang ở đâu, không cần đọc hết dữ liệu thô.

Tính năng:

- Hiển thị project hiện tại và research question.
- Card số liệu: searched papers, Scopus confirmed, undetermined, Keep, PDF uploaded, extracted.
- Timeline gần nhất: search gần nhất, screening gần nhất, upload gần nhất.
- CTA theo trạng thái: thiếu setup thì đi Setup, đã setup thì đi Search & Verify, có bài Keep thì đi Library/Synthesis.

Xử lý kỹ thuật:

- Frontend tổng hợp từ project state và API list/search history.
- Backend nên có endpoint dashboard summary ở P1, MVP có thể aggregate từ các endpoint sẵn có.

### 2. Research Setup

Màn này tạo nền cho search và screening.

Tính năng:

- Nhập/sửa tên project, câu hỏi nghiên cứu, field, khoảng năm.
- Nhập inclusion/exclusion criteria.
- Sinh keyword hoặc Boolean query gợi ý.
- Cho phép dùng query gợi ý để chuyển sang Search & Verify.

Xử lý kỹ thuật:

- Lưu vào `projects`.
- LLM chỉ sinh keyword/query dạng JSON, backend validate trước khi render.
- Criteria thiếu thì vẫn cho search, nhưng screening phải cảnh báo độ tin cậy thấp.

### 3. Search & Verify

Đây là navigation quan trọng nhất của MVP.

Tính năng:

- User nhập query hoặc chọn query gợi ý.
- Hệ thống lấy cố định Top 20 từ Google Scholar.
- Giữ đúng thứ tự Google Scholar trả về.
- Enrich DOI, abstract, ISSN/EISSN nếu thiếu.
- Đối chiếu từng bài với danh mục Scopus.
- Hiển thị badge:
  - `Scopus confirmed`: match được nguồn Scopus.
  - `Coverage ok`: năm bài nằm trong coverage.
  - `Undetermined`: thiếu dữ liệu để kết luận, không gọi là not indexed.
- Summary cards: `found`, `confirmed`, `undetermined`, `duplicates`.
- Có filter để user xem confirmed/undetermined, nhưng default ưu tiên confirmed.
- Có abstract modal, source link, add to Screening/Library.
- History drawer nằm cùng màn, không cần navigation riêng.

Xử lý kỹ thuật:

```text
query
  -> SerpApi Google Scholar, num=20
  -> preserve organic_results order
  -> enrich missing metadata via OpenAlex/Semantic Scholar
  -> normalize DOI, ISSN, EISSN
  -> dedup by DOI or title-author-year in project
  -> Scopus source match by ISSN/EISSN/title
  -> coverage-year check
  -> return counters + verified paper rows
```

Ghi chú UI:

- Không cần selector Top 10/20 nữa.
- Quality Check không nên là tab chính trong flow search. Nó chỉ là action re-check/detail trong từng paper hoặc drawer.

### 4. Screening

Màn này phục vụ quyết định Keep/Remove/Maybe.

Tính năng:

- Bảng các bài từ Search & Verify/Library.
- AI relevance: High, Medium, Low, Insufficient info.
- Lý do match/mismatch với criteria.
- User chọn Keep/Remove/Maybe và ghi note.
- Bulk action tối đa 50 bài/lần.
- Decision history không ghi đè.

Xử lý kỹ thuật:

- LLM nhận research question, criteria và abstract.
- Nếu abstract quá ngắn thì trả `insufficient_info`, không gọi LLM.
- Không hiển thị confidence phần trăm nếu không có cơ sở đo thật.

### 5. Library & Reader

Màn này gom quản lý bài đã giữ, upload PDF và đọc sâu.

Tính năng:

- Danh sách bài Keep.
- Filter theo Scopus status, screening decision, PDF status, extraction status.
- Upload PDF hợp pháp.
- Mở reader hai pane: tài liệu bên trái, note/citation bên phải.
- Hiển thị provenance: page number, snippet, chunk id khi có.

Xử lý kỹ thuật:

- `pdf_status` và `extraction_status` độc lập.
- Upload file giới hạn 20 MB.
- Parse PDF theo trang, lưu chunk có `paper_id`, `page_number`, offsets.
- Embedding vào vector store để dùng cho Synthesis.

### 6. Synthesis

Màn này chỉ tổng hợp từ tài liệu đã ingest, không viết tự do không nguồn.

Tính năng:

- Chọn tập bài đã Keep/extracted.
- Generate outline.
- Chat closed-domain trên tài liệu đã chọn.
- Draft synthesis có citation.
- Click citation để xem snippet/trang nguồn.

Xử lý kỹ thuật:

- Retrieve chunk trước khi draft.
- Claim nào không có evidence thì loại hoặc đánh dấu cần kiểm tra.
- LangGraph điều phối các bước outline, retrieve, draft.

### 7. Export

Màn cuối để user lấy kết quả ra ngoài.

Tính năng MVP:

- Export CSV metadata.
- Export BibTeX.
- Export Markdown synthesis/citation list.

Tính năng P1:

- CSL APA/IEEE/MLA.
- Word/PDF.
- Zotero API.
- Version history.

## Mapping từ UI hiện tại sang UI đề xuất

| UI hiện tại | Trạng thái đề xuất |
|---|---|
| `Overview` | giữ lại, bổ sung counters |
| `Research Setup` | giữ lại |
| `Search Papers` | đổi thành `Search & Verify` |
| `Quality Check` | không để navigation chính; gộp vào `Search & Verify` dưới dạng badge/re-check/detail |
| `Screening` | giữ lại |
| `Library` | đổi thành `Library & Reader`, gộp upload/reader |
| `Synthesis` | giữ lại, có thể kéo bớt phần verification/citation từ workspace |
| `Export` | giữ lại, hiện cần implement thật |

