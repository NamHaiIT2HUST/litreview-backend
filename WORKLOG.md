# Worklog — Team LitReview Agent

> Ghi lại tất cả công việc đã làm theo ngày. Ai làm gì, kết quả gì.
>
> Các mục từ 2026-08-08 trở đi được tổng hợp lại từ lịch sử commit thật (`git log`), gộp theo ngày/người thay vì liệt kê từng commit — cột **Time** để "-" ở những chỗ không có ước lượng giờ gốc.

---

## 2026-09-01

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| ngatt-17 | Viết lại hoàn chỉnh README (cấu trúc thư mục, bảng deliverables), hoàn thiện các doc còn thiếu cho deliverables #2/#4/#6/#8/#9: `docs/journal.md`, `docs/worklog.md`, `docs/ai-logs.md`, `docs/video-demo.md` | ✅ Done | `README.md`, `docs/*.md` | - |
| ngatt-17 | Dọn repo: xóa 9 file doc nội bộ không liên quan (kế hoạch cũ, báo cáo tiến độ), xóa thư mục thư viện ngoài đã vendor (`ai2-scholarqa-lib-main`, `paper-qa-2026.08.12`), gộp `eval_evidence.md` → `evaluation.md`, thêm `uploads/` vào `.gitignore` | ✅ Done | Repo gọn hơn, `.gitignore` cập nhật | - |
| ngatt-17 | Bổ sung bằng chứng đánh giá thật vào `evaluation.md` (deliverable #10): kết quả pytest thật (786 passed, 0 failed, 810 collected), coverage chính xác 61% đo bằng `pytest-cov`, code traceability map, khảo sát người dùng thật (4.25/5 trên 4 người test) | ✅ Done | `docs/evaluation.md` | - |
| ngatt-17 | Chuẩn hóa tên dự án "LitReview Agent" xuyên suốt toàn bộ tài liệu, gắn tag `v1.1` kèm bộ ảnh/slide demo mới | ✅ Done | Toàn bộ `docs/*.md`, `README.md`, `presentation/` | - |
| Hung Nguyen | Thêm pitch deck HTML 10 slide cho Demo Day (bản đầu, sau đó được thay bằng PPTX/PDF trong `v1.1`) | ✅ Done | `presentation/pitch_deck.html` | - |
| Nam Hải | Viết lại `WORKLOG.md` từ dạng liệt kê git-log thô sang bảng công việc theo ngày/người có cấu trúc; thêm script mirror AI log cá nhân (`.ai-log/`) lên Braintrust có redact secret trước khi upload | ✅ Done | `WORKLOG.md`, `scripts/upload_ailog_to_braintrust.py` | - |

**Tổng kết ngày:** Hoàn tất toàn bộ tài liệu deliverables còn thiếu (#2 README, #4 AI Logs, #6 Video Demo, #8 Journal, #9 Worklog, #10 Evaluation) với bằng chứng thật (pytest, coverage, user feedback), dọn sạch tài liệu nội bộ thừa, gắn tag `v1.1`, chuẩn bị pitch deck cho Demo Day.

---

## 2026-08-31

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Nam Hải | Sửa lỗi bảo mật `SECRET_KEY` (code âm thầm dùng key mặc định thay vì dừng khởi động), sửa rò rỉ evidence text vào prompt Writer, sửa đếm sai claim trùng lặp | ✅ Done | `src/config.py`, `src/synthesis/fast_v2/writer.py` | - |
| Nam Hải | Dọn 976 lỗi `ruff` (import order, biến không dùng, one-liner) để CI backend pass, thêm exception có chủ đích trong `ruff.toml` | ✅ Done | CI GitHub Actions xanh cả lint + test | - |
| Nam Hải | Sửa bug xóa đề tài bị tự khôi phục sau F5 (lỗi thứ tự xóa khóa ngoại `PDFChunk`/`PageText`), thêm báo lỗi rõ ràng khi xóa thất bại | ✅ Done | `src/api/project_routes.py`, UI Sidebar/Dashboard | - |
| Nam Hải | Review PR #47/#48 (nhánh `nvh-ui`) bằng quy trình review 10 góc độ, tìm & tự sửa 6 lỗi trước khi merge vào `main` | ✅ Done | Merge PR #48 sạch, không phá vỡ các fix trước đó | - |
| Nam Hải | Sửa giao diện Admin Dashboard: chữ hoa sai chuẩn, màu nền lỗi dark mode, hiển thị token AI thật theo từng tài khoản | ✅ Done | `AdminDashboard.jsx`, `src/api/routes.py` (ghi `SynthesisMetrics`) | - |
| lucasvahust | Chuẩn hóa toàn bộ chữ hoa/thường tiếng Việt, sửa tràn ngang trang, sửa header dính khi cuộn | ✅ Done | UI/UX polish trên nhiều component | - |

**Tổng kết ngày:** Đóng hoàn toàn CI/CD (lint + test đều xanh lần đầu tiên), vá 1 lỗ hổng bảo mật thật (SECRET_KEY fallback công khai trong source), và xử lý dứt điểm bug mất dữ liệu khi xóa đề tài.

---

## 2026-08-30

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Nam Hải | Xây trang Admin Dashboard: xem danh sách tài khoản, số lượt tra cứu, token AI đã dùng theo từng người | ✅ Done | `AdminDashboard.jsx` + API `/auth/admin/stats` | - |
| Nam Hải | Sửa luồng đăng nhập admin (tour onboarding kéo nhầm tab, ép admin luôn vào đúng trang Quản trị), cho phép username không phải email đăng nhập | ✅ Done | `App.jsx`, `AuthModal.jsx`, `HorizontalNavbar.jsx` | - |

**Tổng kết ngày:** Hoàn thiện role admin end-to-end theo yêu cầu — xem được toàn bộ tài khoản, số liệu sử dụng, không lẫn với trải nghiệm researcher thường.

---

## 2026-08-29

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Nam Hải | Merge PR #46 (UI/UX overhaul lớn), tự phát hiện & sửa 5 lỗi trước khi merge để không phá vỡ bản đang chạy cloud | ✅ Done | Merge sạch vào `main`, giữ nguyên chức năng cloud | - |
| Nam Hải | Sửa chatbot RAG không trả lời được câu hỏi về tác giả/tên bài báo (lỗi sắp xếp trang trong query lấy metadata) | ✅ Done | `src/api/routes.py` (`/workspace/chat`) | - |
| Nam Hải | Gắn citation theo từng đoạn văn (per-paragraph), hiển thị chỉ số chất lượng Tier1/2 thật thay vì số giả | ✅ Done | `src/synthesis/fast_v2/` | - |
| Hung Nguyen, lucasvahust | Làm việc trên nhánh `nvhung-fix-test` / UI update | ✅ Done | Merge vào `fix/test` | - |

**Tổng kết ngày:** Review + merge an toàn 1 PR lớn, sửa 2 bug người dùng thật đang gặp (chatbot cứng nhắc, chỉ số citation sai).

---

## 2026-08-28

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Nam Hải | Huấn luyện & chọn model NLI cho Module 1 (Evidence Quantification), đưa `ragas_eval_service` tính điểm RAGAS thật thay vì giả lập | ✅ Done | `models/nli_evidence_v1`, `src/services/ragas_eval_service.py` | - |
| Nam Hải | Đưa các cải tiến độ chính xác synthesis từ nhánh thử nghiệm vào `fast_v2`, đổi embedding model sang MiniLM để hết timeout trên EC2 cấu hình nhỏ | ✅ Done | `src/synthesis/fast_v2/` | - |

**Tổng kết ngày:** Đóng gói xong Module 1 (đánh giá bằng chứng bằng model NLI tự train) và ổn định hiệu năng synthesis trên hạ tầng thật.

---

## 2026-08-27

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Nam Hải | Sửa AI Screening bị lẫn dữ liệu giữa các đề tài, chặn các trường hợp AI tự bịa kết quả khi thiếu dữ liệu (silent fabrication) | ✅ Done | Nhiều route trong `src/api/` | - |
| Nam Hải | Tách LLM theo tab: Cấu hình/Tìm kiếm dùng OpenAI gpt-4o-mini, Phân tích dữ liệu dùng DeepSeek riêng để tránh hết quota Gemini | ✅ Done | `src/services/llm/router.py` | - |
| Nam Hải | Sửa lỗi không tải được báo cáo synthesis đã hoàn thành khi load lại trang, sửa lỗi tràn layout | ✅ Done | Workspace/Synthesis panel | - |

**Tổng kết ngày:** Vá loạt lỗi ảnh hưởng trực tiếp trải nghiệm người dùng thật (dữ liệu lẫn lộn, AI bịa kết quả, mất report khi F5).

---

## 2026-08-26

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Nam Hải | Chuẩn hóa xác thực Google thật, tạo project tức thì, mỗi agent Gemini có key riêng, kiểm tra quyền sở hữu project | ✅ Done | `src/api/auth_routes.py`, `ProjectContext.jsx` | - |
| Nam Hải | Sửa mở notebook bị treo 30 giây, giảm còn tức thời | ✅ Done | `PersonalizedDashboard.jsx` | - |
| liemnd4 | Gom toàn bộ lựa chọn LLM provider qua 1 router duy nhất có kiểm tra năng lực model, khôi phục tài khoản demo thành tài khoản thật, ép buộc xác thực API + chặn fallback âm thầm | ✅ Done | `src/services/llm/router.py`, security hardening | - |

**Tổng kết ngày:** Củng cố tầng xác thực + LLM routing — không còn fallback âm thầm che giấu lỗi thật, đăng nhập Google ổn định.

---

## 2026-08-25

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Nam Hải | Chuyển hạ tầng deploy sang AWS EC2 (13.212.121.28), cấu hình Google OAuth Client ID cho domain thật `c3-app-165.io.vn` | ✅ Done | Vercel proxy + EC2 backend live | - |
| Nam Hải | Xử lý fallback an toàn khi thiếu Gemini key hoặc key lỗi, dùng `safeFetch` xuyên suốt frontend để tránh lỗi kết nối backend | ✅ Done | `vector_store.py`, `apiConfig.js` | - |
| ngatt-17 | Tích hợp các tính năng từ nhánh cá nhân vào `main` | ✅ Done | Merge `feature/ngaedit-integration` | - |

**Tổng kết ngày:** Chính thức lên production trên EC2 + domain riêng — mốc quan trọng cho yêu cầu "Live URL" của deliverables.

---

## 2026-08-24

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Nam Hải | Sửa hàng loạt lỗi UI landing page (header, responsive, favicon), tối ưu Docker (cài torch bản CPU-only để giảm 2.5GB, tránh OOM trên free tier) | ✅ Done | `Dockerfile`, `PublicLandingPage.jsx` | - |
| liemnd4 | Wire semantic verification vào fast_v2, thêm grounded literature synthesis, dọn Docker cài PyTorch CPU-only | ✅ Done | `src/synthesis/fast_v2/` | - |

**Tổng kết ngày:** Ngày làm việc nặng nhất (~110 commit gộp 2 người) — dồn sức ổn định deploy Docker và nâng cấp pipeline synthesis fast_v2.

---

## 2026-08-23

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| liemnd4 | Khôi phục fast_v2 khớp với pipeline evidence đã kiểm chứng, gắn cross-encoder reranker thật, thêm bộ đo thời gian từng giai đoạn | ✅ Done | `src/synthesis/fast_v2/` | - |
| lucasvahust | Redesign giao diện học thuật toàn diện, thêm Google OAuth, quản lý project, tour hướng dẫn, tối ưu dark/light mode | ✅ Done | Frontend UI/UX overhaul | - |
| ngatt-17 | Tích hợp module Phân tích dữ liệu (EDA) vào `develop`, thêm adaptive RAG | ✅ Done | Data Analysis tab | - |

**Tổng kết ngày:** 3 mảng lớn chạy song song: pipeline synthesis (backend), UI/UX toàn diện (frontend), và module Phân tích dữ liệu — merge gộp thành công vào `develop`.

---

## 2026-08-22

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Nam Hải | Thêm hệ thống xác thực, phân quyền theo role, và admin dashboard (phiên bản đầu tiên) | ✅ Done | `feat(auth)` | - |
| Nam Hải | Hoàn thiện tích hợp multi-agent Phase 2 và pipeline finetune model | ✅ Done | Merge PR #36 | - |
| ngatt-17 | Sửa lỗi hallucination của chatbot, lỗi phân tích dữ liệu | ✅ Done | - | - |

**Tổng kết ngày:** Đặt nền móng đầu tiên cho hệ thống phân quyền/admin — tiền đề cho Admin Dashboard hoàn chỉnh ở tuần sau.

---

## 2026-08-21

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| ngatt-17 | Bản đầu tiên chatbot + module literature | ✅ Done | `chatbot+liter v1` | - |

---

## 2026-08-20

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Nam Hải | Benchmark & tích hợp reranker học thuật fine-tune riêng cho 3 domain (đạt 98.55% AP) | ✅ Done | `src/synthesis/fast_v2/selection/` | - |
| liemnd4 | Ổn định RAG grounded answer generation (chỉnh temperature + rule từ chối), viết guide migration embedding provider cho team | ✅ Done | `docs/`, `src/services/rag_service.py` | - |

**Tổng kết ngày:** Reranker tự huấn luyện đạt độ chính xác cao (98.55% AP) — cải thiện trực tiếp chất lượng chọn evidence cho synthesis.

---

## 2026-08-19

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Nam Hải | Thêm tính năng tóm tắt bài báo tự động (TL;DR) có xử lý paywall | ✅ Done | `feat(search)` | - |

---

## 2026-08-18

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Nam Hải | Merge nhánh multi-agent setup-search, thêm agent Citation Genealogy (snowballing 2 chiều), viết guide fine-tuning pipeline đầy đủ | ✅ Done | Merge PR #35, `docs/guide/` | - |
| liemnd4 | Ground evidence quote thẳng vào text gốc nguồn (raw source), tránh trích dẫn sai lệch | ✅ Done | Citation grounding | - |

**Tổng kết ngày:** Mở rộng hệ agent với module Citation Genealogy — cho phép truy vết bài báo liên quan 2 chiều (trước/sau).

---

## 2026-08-17

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Nam Hải | Ổn định lựa chọn LLM provider (thử GoRouter, revert lại Gemini), tự động lọc/parse nhiều Gemini key, thêm fallback production khi backend local lỗi | ✅ Done | `src/config.py`, `apiConfig.js` | - |
| liemnd4 | Xây multi-agent supervisor graph theo Phase 2 Master Plan | ✅ Done | `src/agents/slr_swarm/` | - |

---

## 2026-08-16

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Nam Hải | Ngày commit nhiều nhất tuần (52 commit): sửa cascading xóa tài liệu, đồng bộ session synthesis khi refresh, tích hợp backend Export tab, cấu hình `VITE_API_BASE` động cho Vercel, tự động migrate schema Postgres, deploy guide đầy đủ cho local/Supabase/Render/Vercel | ✅ Done | Nhiều route API + docs deploy | - |
| liemnd4 | Sửa luồng evidence + workspace của synthesis | ✅ Done | - | - |
| ngatt-17 | Thêm lịch sử phiên làm việc | ✅ Done | - | - |

**Tổng kết ngày:** Ngày dồn nhiều nhất để chuẩn bị deploy thật (Render/Supabase/Vercel) — bao gồm loạt fix schema Postgres và deploy guide chi tiết.

---

## 2026-08-15

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Nam Hải | Sửa crash màn hình trắng React, sửa PyMuPDF fallback sang pypdf, cô lập nguồn workspace theo direct upload, ép chuẩn RAG chat kiểu NotebookLM | ✅ Done | `WorkspaceTab.jsx`, `document_processor.py` | - |
| ngatt-17 | Merge tính năng synthesis từ nhánh workspace-ui-layout | ✅ Done | - | - |

---

## 2026-08-14

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Nam Hải | Merge nhiều nhánh (`nga`, `feature/workspace-ui-layout`) vào `develop`, xử lý xung đột routes | ✅ Done | Merge PR #30, #31 | - |
| liemnd4 | Refine layout workspace theo scope, thêm evidence-first synthesis pipeline | ✅ Done | - | - |

---

## 2026-08-13

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Nam Hải | Viết Phase 2 Implementation Plan và System Architecture Context | ✅ Done | `Phase2_Implementation_Plan.md` | - |
| liemnd4 | Thiết kế + lên kế hoạch tối ưu synthesis pipeline, thêm evidence-first literature review synthesis | ✅ Done | - | - |

---

## 2026-08-12

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Nam Hải | Ngày merge nhiều nhánh nhất (18 commit): gộp Research Setup + Search & Verify + Synthesis + Workspace từ nhiều nhánh song song, refactor SearchTab điều hướng sang Workspace | ✅ Done | Merge tổng hợp lớn | - |
| lucasvahust | Hoàn thiện Module M6 Export (BibTeX, CSV, Markdown, JSON) | ✅ Done | `export_service.py` | - |

**Tổng kết ngày:** Gộp thành công nhiều nhánh tính năng song song (Setup, Search, Synthesis, Workspace, Export) thành 1 luồng thống nhất — bước ngoặt hợp nhất sản phẩm.

---

## 2026-08-11

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Nam Hải | Merge 4 PR liên tiếp (#25–#28) hợp nhất `develop`/`stagging`, giải quyết xung đột search filters | ✅ Done | - | - |
| liemnd4 | Triển khai Evidence-Driven Synthesis & Ingestion Provenance, sửa race condition outbox, dispatch async Celery task cho vector cleanup | ✅ Done | `src/services/vector_cleanup_service.py` | - |

---

## 2026-08-10

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Nam Hải | Refactor luồng search-verify, cập nhật phân chia task, thêm utility scripts | ✅ Done | - | - |

---

## 2026-08-08

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Nam Hải | Đồng bộ schema DB, sửa lỗi validate Pydantic, hoàn thiện frontend Module 4 (Quality Verification), sửa insert UUID + thêm UX hiển thị Quartile | ✅ Done | Module 4 hoàn chỉnh | - |

---

## 2026-08-06

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Nam Hải | Xây dựng não bộ RAG (LangChain + Gemini 1.5 Flash) trả lời câu hỏi | ✅ Done | API `POST /workspace/chat` | 1.5h |
| Nam Hải | Tích hợp Vector Database (ChromaDB) và Google Embeddings | ✅ Done | API `GET /workspace/test-search` | 2h |
| Nam Hải | Viết Ingestion Pipeline (Upload PDF, bóc tách và cắt chunk bằng LangChain) | ✅ Done | API `POST /workspace/upload` | 2h |
| Nam Hải | Ẩn bảo mật 3 API Keys Google Gemini vào biến môi trường `.env` | ✅ Done | Tăng tính bảo mật cho Repo | 0.5h |

**Tổng kết ngày:** Hoàn thiện 100% Core Logic Backend cho hệ thống RAG (Upload -> Chunking -> VectorDB -> LLM RAG Chat). API đã sẵn sàng để Frontend kết nối.

---

## 2026-08-05

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Nam Hải | Thiết lập hệ thống AI Logging tự động qua Git pre-push hook | ✅ Done | Script nộp log tự động | 1.5h |
| Nam Hải | Xử lý Merge Conflict (nhánh develop & feature/nga-test-setup) | ✅ Done | Gộp thành công luồng API và UI Search | 1h |
| Nam Hải | Khắc phục lỗi thiếu thư viện và setup môi trường backend (`sqlalchemy`, `aiosqlite`) | ✅ Done | Server chạy ổn định trên nhánh develop | 0.5h |
| Nam Hải | Mở rộng API `/search`: tăng `limit` mặc định từ 10 lên 20 | ✅ Done | Cập nhật file `routes.py` | 0.5h |
| Nam Hải | Lên phương án tích hợp API Scopus & Web of Science và phân chia MVP Task | ✅ Done | Tài liệu Implementation Plan | 1.5h |
| liemnd4 | Triển khai Scopus Journal Verification & UI status badges | ✅ Done | Code `scopus_matcher.py` trên nhánh develop | - |
| lucasvahust | Thêm bộ lọc tài liệu, sắp xếp đa chiều và tích hợp OpenAlex abstract | ✅ Done | UI Filter & Backend OpenAlex fetcher | - |
| ngatt-17 | Xử lý Pull Request, update luồng giao diện tìm kiếm | ✅ Done | Merge PR thành công | - |

**Tổng kết ngày:** Team đã hoàn tất tích hợp nhiều nguồn dữ liệu thực tế (Scopus verification, OpenAlex, Semantic Scholar), xử lý triệt để các lỗi conflict và chốt xong lộ trình chạy nước rút MVP Phase 1.

---

## 2026-08-04

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Nam Hải | Xây dựng API tích hợp SerpApi & Semantic Scholar với cơ chế BYOK | ✅ Done | API `scholar_api.py` hoạt động | - |
| Nam Hải | Viết tài liệu `RUN_GUIDE.md` và dọn dẹp dữ liệu giả lập (mock data) | ✅ Done | Tài liệu hướng dẫn chi tiết | - |
| ngatt-17 | Nâng cấp giao diện trang tìm kiếm (F5 search) | ✅ Done | Update UI component | - |
| ngatt-17 | Sửa các lỗi linting (Ruff) để hệ thống vượt qua CI checks | ✅ Done | Pass CI tests | - |

**Tổng kết ngày:** Hoàn thiện luồng Backend cơ bản với dữ liệu thật từ API, loại bỏ toàn bộ dữ liệu giả.

---

## 2026-08-03

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Nam Hải | Thiết kế và tái cấu trúc giao diện Frontend (React/Vite) thành Component | ✅ Done | Giao diện Search & Workspace cơ bản | - |
| Nam Hải | Áp dụng TailwindCSS, Google Fonts và template MotaAdmin | ✅ Done | Giao diện trực quan, thân thiện (UI/UX) | - |
| Nam Hải | Xây dựng luồng tải file nhiều bước (multi-step upload) cho RAG Workspace | ✅ Done | Frontend Workflow | - |

**Tổng kết ngày:** Dựng xong bộ khung Frontend theo hướng Component-based, sẵn sàng cho việc kết nối API.

---

## 2026-07-27

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Ngaaa | Test các công cụ AI logging và viết tài liệu ghi chép | ✅ Done | Log documentation | - |
