# Development Journal — P-165 LitReview Agent

> Nhật ký phát triển ghi lại các quyết định kỹ thuật, khó khăn và bài học của team qua 6 tuần xây dựng hệ thống.

**Team:** Nguyễn Đình Liêm · Tạ Thị Nga · Nguyễn Văn Hưng · Nguyễn Đào Nam Hải  
**Dự án:** LitReview Agent  
**Chương trình:** AI Engineering Cohort 3 — AI20K Build Phase

---

## Week 1: Tháng 7/2026 — Khởi tạo & Thiết kế nền tảng

### Mục tiêu
- [x] Xác định bài toán và phạm vi dự án
- [x] Thiết kế kiến trúc tổng thể hệ thống
- [x] Setup môi trường phát triển, khởi tạo repo GitHub
- [x] Xây dựng UI/UX template ban đầu với React + Vite

### Đã hoàn thành
- Khởi tạo project với cấu trúc `src/` (backend FastAPI) + `frontend/` (React Vite)
- Xây dựng giao diện UI/UX đầu tiên với TailwindCSS — thiết kế theo phong cách NotebookLM
- Tích hợp SerpApi để tìm kiếm Google Scholar
- Thêm module tích hợp Semantic Scholar và tính LitScore ban đầu
- Setup Copilot Chat + Gemini CLI thành công

### Quyết định kỹ thuật
- **Chọn FastAPI** thay vì Django/Flask: vì async-first, phù hợp với LangGraph pipeline và auto-generate OpenAPI docs
- **Chọn React + Vite** thay vì Next.js: deploy tĩnh trên Vercel đơn giản hơn, load nhanh hơn
- **Chọn LangChain/LangGraph** làm AI orchestration layer: có sẵn tích hợp Gemini, support agentic workflow

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|----------|-----------|---------|
| Import lỗi `xlsx` trong frontend | Refactor thành modular components, tách rõ concerns | Resolve hoàn toàn |
| UI dark mode text bị invisible | Fix CSS variable override cho dark mode | UI hoạt động đúng |

### Bài học
- Bắt đầu với cấu trúc thư mục rõ ràng từ đầu tiết kiệm rất nhiều thời gian refactor sau này
- Nên dùng `docker-compose` để quản lý DB ngay từ tuần 1, tránh mỗi máy cài khác nhau

---

## Week 2: Cuối tháng 7/2026 — Scopus Verification & RAG Foundation

### Mục tiêu
- [x] Implement Scopus journal verification (xác minh bài báo thuộc danh mục Scopus)
- [x] Xây dựng vector store với ChromaDB
- [x] Tích hợp PDF ingestion và text extraction

### Đã hoàn thành
- Import 48K records Scopus vào database — đây là bước breakthrough để verify bài báo offline
- Implement matching ISSN / tên tạp chí với OpenAlex API làm fallback
- Tích hợp ChromaDB làm vector store cho RAG pipeline
- Module PDF ingestion: extract text bằng PyMuPDF, tự động chunk + embed vào ChromaDB
- Implement LangChain RAG chat API với Gemini 1.5 Flash

### Quyết định kỹ thuật
- **Chọn ChromaDB** thay vì Pinecone/Weaviate: chạy local, không cần API key, phù hợp demo
- **Dùng Gemini embedding model** (`models/gemini-embedding-2`): cost thấp, chất lượng tốt cho academic text
- **Persist Scopus records trong PostgreSQL** thay vì check API real-time: giảm latency từ ~3s xuống ~50ms per paper

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|----------|-----------|---------|
| Scopus matching accuracy thấp (nhiều false negative) | Thêm CrossRef API enrichment, ISSN normalization, extract journal name từ Scholar summary | Đạt ~90%+ match rate |
| Gemini embedding model name thay đổi | Pin version `embedding-001` rồi migrate sang `models/gemini-embedding-2` | Stable |
| LangSmith tracing lỗi 403 | Disable LangSmith trong dev, chỉ enable production | RAG chat hoạt động ổn định |

### Bài học
- Import data offline (Scopus records) tốt hơn nhiều so với gọi API real-time — cả về tốc độ lẫn chi phí
- Embedding model version cần được pin cụ thể trong `requirements.txt`, không dùng `latest`

---

## Week 3: Đầu tháng 8/2026 — AI Screening & Quality Check

### Mục tiêu
- [x] Implement AI Screening với Gemini LLM (Include/Exclude papers)
- [x] Xây dựng Quality Check module (Journal Quartile Q1-Q4)
- [x] Fix các bugs nghiêm trọng về UUID và database schema
- [x] Migrate từ SQLite sang PostgreSQL

### Đã hoàn thành
- Module AI Screening: Gemini đọc `Title + Abstract + Criteria` → quyết định Include/Exclude với score 1-3
- Implement Journal Quartile verification (Q1/Q2/Q3/Q4) và Open Access status
- Fix bug UUID insertion trong PostgreSQL (kiểu dữ liệu mismatch)
- Migration hoàn toàn từ SQLite sang PostgreSQL + Alembic migrations
- Setup Alembic cho schema versioning

### Quyết định kỹ thuật
- **Dùng Pydantic Output Parser** cho LLM response: đảm bảo structured output, tránh crash khi LLM trả về text tự do
- **Chuyển sang PostgreSQL** từ SQLite: cần full-text search, UUID support, concurrent connections cho production
- **Strict Scopus-only filtering**: chỉ giữ bài báo confirmed Scopus, loại bỏ unverified papers — đây là USP của sản phẩm

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|----------|-----------|---------|
| UUID comparison lỗi khi delete query | Convert `project_id` UUID đúng type trước khi compare | Fix hoàn toàn |
| LLM reject abstract ngắn | Relax ngưỡng minimum abstract length | Screening hoạt động với abstract ngắn |
| PostgreSQL connection lỗi khi deploy | Load dotenv trong `database.py` trước khi init engine | Backend kết nối ổn định |

### Bài học
- Nên viết Pydantic schema cho mọi LLM output từ đầu — không tin response text tự do
- Database migration cần Alembic từ sớm, không để "migrate tay" sau này rất khó

---

## Week 4: Giữa tháng 8/2026 — Synthesis Pipeline & Export

### Mục tiêu
- [x] Xây dựng Synthesis pipeline với LangGraph (literature review tự động)
- [x] Implement Export module (Excel, BibTeX, CSV, Markdown)
- [x] Fix race condition trong synthesis pipeline
- [x] Integrate evidence-first synthesis approach

### Đã hoàn thành
- Synthesis pipeline: LangGraph orchestrate nhiều agents — outline → section writer → citation grounding
- Implement bounded batch dispatch với state machine: `pending → queued → processing → done`
- Export module hoàn chỉnh: BibTeX, CSV, Markdown, JSON, Excel với full Unicode support (tiếng Việt)
- Evidence-first synthesis: mỗi claim phải có DOI grounded citation, không fabricate
- Fix race condition trong outbox pattern, fail-closed claim verification

### Quyết định kỹ thuật
- **Evidence-first approach**: synthesis chỉ được viết những gì có evidence từ PDF đã upload — chống hallucination
- **LangGraph state machine** thay vì sequential calls: cho phép retry individual steps, không cần restart toàn bộ
- **Celery async tasks** cho synthesis: process không block API thread, user thấy progress real-time

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|----------|-----------|---------|
| Race condition: 2 workers cùng claim 1 task | Implement fail-closed claim verification với DB lock | Resolve hoàn toàn |
| Celery task không dispatch đúng | Fix async dispatch pattern, add full traceback logging | Stable |
| Export Excel lỗi font tiếng Việt | Fix encoding UTF-8 với openpyxl | File mở đúng trên Excel |

### Bài học
- Agentic pipeline cần state machine rõ ràng — không dùng simple sequential calls
- Celery + Redis là combo tốt cho background tasks, nhưng cần test kỹ race condition

---

## Week 5: Cuối tháng 8/2026 — Fine-tuning & Benchmark

### Mục tiêu
- [x] Fine-tune Llama-3-8B với LoRA cho 3 chuyên gia agents
- [x] Chạy benchmark đánh giá chất lượng 3 agents
- [x] Implement academic cross-encoder reranker
- [x] NLI evidence quantification model

### Đã hoàn thành
- Fine-tune thành công 3 LoRA adapters: `lora_agent1_scope`, `lora_agent2_criteria`, `lora_agent3_pico`
- Benchmark kết quả: **99.2% JSON accuracy, 100% PICO schema compliance** trên 120 test cases (3 domains)
- Train NLI model để quantify evidence support (Tier 1 exact-match, Tier 2 semantic)
- RAG pipeline optimization: **82% time reduction** (46.95s → 8.44s), RAGAS faithfulness 0.88
- Deploy benchmark scripts tự động hóa evaluation

### Quyết định kỹ thuật
- **PEFT/LoRA với Unsloth**: giảm VRAM 4x so với full fine-tune, training nhanh hơn 2x
- **3 specialized agents** thay vì 1 general agent: mỗi agent chuyên sâu 1 task → accuracy cao hơn
- **Llama-3-8B** thay vì larger models: đủ capable cho structured output, deploy được trên free tier GPU

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|----------|-----------|---------|
| Agent 2 fail 1/41 JSON syntax | Retry với temperature thấp hơn | 97.6% stable |
| Embedding timeout trên EC2 nhỏ | Swap sang MiniLM (nhẹ hơn) | Sub-second embedding |
| RAGAS eval trả về mock data | Fix `ragas_eval_service` để compute real scores | Real metrics |

### Bài học
- Fine-tuning với structured output (JSON schema) cần dataset cực kỳ consistent — 1 lỗi format làm drop accuracy
- Benchmark nên chạy automated từ đầu, không đánh giá manual

---

## Week 6: Tháng 9/2026 — Production & Polish

### Mục tiêu
- [x] UI/UX overhaul toàn bộ frontend
- [x] Xây dựng Admin dashboard
- [x] Security hardening và fix các bugs trước Demo Day
- [x] Deploy production tại https://www.c3-app-165.io.vn/
- [x] Hoàn thiện toàn bộ tài liệu deliverables (README, journal, worklog, AI logs, evaluation evidence)

### Đã hoàn thành
- UI/UX overhaul hoàn toàn — landing page mới, responsive, dark mode
- Admin dashboard: per-user token usage, query counts, LLM cost tracking
- Security: restore fail-closed SECRET_KEY validation, fix cross-project data leak
- Google OAuth integration cho production domain `c3-app-165.io.vn`
- Fix 5 confirmed bugs trước merge: overflow, citation race condition, navbar truncation, etc.
- Deploy AWS EC2 backend + Vercel frontend proxy
- Viết lại README hoàn chỉnh, dọn repo (xóa doc nội bộ + thư viện vendor không liên quan), gộp `eval_evidence.md` → `evaluation.md`
- Bổ sung bằng chứng đánh giá thật vào `evaluation.md`: kết quả pytest thật (786 passed, 810 collected), coverage 61% đo bằng `pytest-cov`, code traceability map, khảo sát người dùng thật (4.25/5 trên 4 người test)
- Viết lại `WORKLOG.md` từ liệt kê git-log thô sang bảng công việc theo ngày/người; thêm script mirror AI log cá nhân lên Braintrust (có redact secret)
- Gắn tag `v1.1`, chuẩn bị pitch deck cho Demo Day

### Quyết định kỹ thuật
- **AWS EC2 + Vercel proxy** thay vì Render: cần control deployment environment, Render cold start quá chậm
- **Google OAuth** thay vì email-only: UX tốt hơn cho demo, không cần nhớ password
- **Admin token tracking**: BTC có thể verify team thực sự dùng AI, không fake

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|----------|-----------|---------|
| POST request bị 308 redirect (HTTP → HTTPS) | Route requests qua www origin, fix safeFetch | API calls stable |
| Google OAuth fail trên production domain | Update Google Cloud Console với đúng `c3-app-165.io.vn` | Login hoạt động |
| LLM fabricate citations | Add anti-fabrication guards trong writer prompt | 0 fabricated citations |

### Bài học
- Security cần được nghĩ từ đầu, không phải patch ở cuối — cross-project data leak rất khó fix sau
- Luôn test trên production domain trước Demo Day — localhost behaviour khác production rất nhiều
