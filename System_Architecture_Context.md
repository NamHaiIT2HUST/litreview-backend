# Bối cảnh & Kiến trúc Hệ thống (Module Research Setup & Search/Verify)

Tài liệu này (System_Architecture_Context.md) được tạo ra nhằm cung cấp ngữ cảnh (Context) cho các LLM hoặc AI Agent khác khi tham gia vào quá trình phát triển (đặc biệt là Phase 2).

## 1. Công nghệ Sử dụng (Tech Stack)
*   **Backend:** Python, FastAPI, SQLAlchemy (Async), Uvicorn.
*   **Database:** SQLite (Async bằng thư viện `aiosqlite`).
*   **Frontend:** React 19 (Vite), Tailwind CSS v3, Lucide React (Icons).
*   **External APIs:** SerpApi (để crawl Google Scholar), Semantic Scholar API, OpenAlex API (để lấy Full Abstract và TL;DR), Scopus/SJR (dữ liệu chất lượng tĩnh hoặc qua API nếu có).

## 2. Các Modules Hiện Tại (Phase 1)
Hệ thống hiện tại đang hoàn thiện luồng làm việc cơ bản bao gồm 4 tab (Navigation): Overview, Research Setup, Search & Verify, và Workspace / Export. Dưới đây là chi tiết 2 module cốt lõi:

### 2.1. Module: Research Setup (Cấu hình Nghiên cứu)
*   **Mục đích:** Nơi người dùng nhập thông tin về đề tài nghiên cứu.
*   **Dữ liệu đầu vào (Input):**
    *   Tên dự án, Lĩnh vực nghiên cứu (Domain).
    *   Câu hỏi nghiên cứu (Research Question - RQ).
    *   Tiêu chí lựa chọn (Inclusion Criteria).
    *   Tiêu chí loại trừ (Exclusion Criteria).
*   **Luồng xử lý (Data Flow):**
    *   Người dùng nhập thông tin qua UI (React).
    *   Frontend gọi API `POST /projects` để lưu vào DB (bảng `projects`).
    *   Backend sử dụng logic sinh từ khóa (Keyword Generation) - hiện tại có thể dùng một số hàm rule-based tĩnh hoặc prompt cơ bản - để đề xuất chuỗi tìm kiếm Boolean (ví dụ: `"ECG signal" AND "1D CNN"`).

### 2.2. Module: Search & Verify (Tìm kiếm & Xác minh)
*   **Mục đích:** Nhận chuỗi Boolean từ Research Setup để crawl báo từ Google Scholar và xác minh chất lượng trên Scopus.
*   **UI/UX:**
    *   Thanh tìm kiếm hỗ trợ nhập nhiều thẻ (Tags/Chips) thay vì một chuỗi dài.
    *   Có Lịch sử tìm kiếm (Search History) hiển thị các truy vấn cũ.
    *   Hiển thị thẻ bài báo (Card View) với thông tin: Title, Authors, Journal, Year, Abstract (có thể mở rộng), TL;DR (nếu có), nhãn "Scopus Indexed", và nút "AI Screening".
*   **Luồng xử lý (Data Flow):**
    1.  Frontend gửi `query_string` lên `POST /projects/{id}/search`.
    2.  Backend gọi `SerpApi` (hoặc Semantic Scholar) để lấy top N kết quả.
    3.  Backend chạy hàm `_persist_search`:
        *   Tạo bản ghi trong `search_queries` lưu lại lịch sử.
        *   Đối chiếu với Scopus/SJR để dán nhãn (`scopus_status = 'indexed' | 'undetermined'`).
        *   Crawl thêm dữ liệu (Full Abstract, TL;DR) từ OpenAlex / Semantic Scholar nếu có.
        *   Lưu các bài báo vào bảng `papers`.
    4.  API trả về danh sách các bài báo **đã được xác minh Scopus** (filter `scopus_status == 'indexed'`) và chặn trần số lượng (VD: max 20 bài).

## 3. Cấu trúc Database (Lược đồ quan hệ)
Dưới đây là các bảng chính liên quan đến 2 module này:

*   **`projects` (Dự án):**
    *   `id` (UUID, PK), `name`, `research_field`, `research_question`, `criteria_include` (JSON), `criteria_exclude` (JSON).
*   **`search_queries` (Lịch sử tìm kiếm):**
    *   `id` (UUID, PK), `project_id` (FK), `query_string`, `strategy_label`, `result_count`, `created_at`.
*   **`papers` (Bài báo):**
    *   `id` (UUID, PK), `project_id` (FK), `doi`, `title`, `authors` (JSON), `journal`, `year`, `abstract`, `tldr`.
    *   `scopus_status` (Enum: `indexed`, `not_indexed`, `undetermined`).
    *   `scopus_quartile` (String: Q1, Q2...).
    *   `dedup_key` (Chuỗi mã hóa để chống trùng lặp dữ liệu).
*   **`screening_decisions` (Kết quả Lọc AI):**
    *   `id` (PK), `paper_id` (FK), `decision` (Enum: `include`, `exclude`, `maybe`), `reasoning` (Văn bản giải thích lý do AI đưa ra quyết định dựa trên criteria).

## 4. Gợi ý cho Các Agent LLM Khác (Khi Đọc Tài Liệu Này)
*   **Định hướng Phase 2:** Hệ thống sẽ chuyển dịch từ *Tool* sang *Multi-Agent Swarm*. Cần chú ý đến khả năng giao tiếp bất đồng bộ giữa các Agent (như Agent thu thập PDF, Agent đọc Abstract mù đôi).
*   **Lưu ý khi Code:** Frontend React được build bằng Vite. Các component được module hóa chặt chẽ (VD: `SearchTab.jsx`, `PaperTable.jsx`). Backend FastAPI sử dụng kiến trúc chuẩn với `routes`, `services`, và `models`. Cần đảm bảo `AsyncSession` được quản lý đúng cách khi ghi/đọc DB.
