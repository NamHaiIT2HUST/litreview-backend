# Worklog — Team LitReview Agent

> Ghi lại tất cả công việc đã làm theo ngày. Ai làm gì, kết quả gì.

---

## 2026-08-06

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Nam Hải | Tích hợp Vector Database (ChromaDB) và Google Embeddings | ✅ Done | API `GET /workspace/test-search` | 2h |
| Nam Hải | Viết Ingestion Pipeline (Upload PDF, bóc tách và cắt chunk bằng LangChain) | ✅ Done | API `POST /workspace/upload` | 2h |
| Nam Hải | Ẩn bảo mật 3 API Keys Google Gemini vào biến môi trường `.env` | ✅ Done | Tăng tính bảo mật cho Repo | 0.5h |

**Tổng kết ngày:** Xây dựng thành công tiền đề cho hệ thống RAG (Nhận file PDF, lưu trữ, nhúng Vector và tìm kiếm tương đồng trên ChromaDB). Đã sẵn sàng kết nối API Chatbot cuối cùng.

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
