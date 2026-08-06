# Báo cáo Cộng tác AI (AI Collaboration Log)

Tài liệu này tổng hợp lại các công việc, tính năng và tư vấn kiến trúc mà AI (Antigravity) và Người dùng (Nam Hải) đã cùng nhau thực hiện để xây dựng dự án **LitReview Agent**.

## 1. Tích hợp Hệ thống Đánh giá tự động (AI Logging & Git Hooks)
- **Vấn đề:** Cần hệ thống tự động ghi nhận và nộp log (lịch sử làm việc với AI) lên server chấm điểm của giảng viên mỗi khi push code.
- **Giải pháp:**
  - Viết script `scripts/setup_hooks.ps1` để tự động cài đặt Git Hook (`pre-push`).
  - Viết script `scripts/log_antigravity.py` và `scripts/submit_log.py` để quét thư mục `.gemini/antigravity/brain`, trích xuất các file `transcript.jsonl` và format lại chuẩn đầu ra.
  - Tích hợp thành công `AI_LOG_API_KEY` (BYOK) vào file `.env`.
  - Đã nộp thành công hàng trăm log lên server chấm điểm.

## 2. Quản lý Nhánh (Branch) & Xử lý Xung đột (Merge Conflicts)
- **Vấn đề:** Gặp conflict code phức tạp khi merge nhánh `feature/nga-test-setup` vào nhánh `develop`, đặc biệt tại các file `SearchTab.jsx`, `schemas.py` và `scholar_api.py`.
- **Giải pháp:**
  - AI đã phân tích luồng code, gỡ rối conflict bằng cách giữ lại các UI Component mới của nhánh Nga (Search History, Filters) và kết hợp với logic gọi API mới của nhánh Develop.
  - Sửa lỗi linting của thư viện `Ruff` liên quan đến chuẩn đặt tên biến `litScore` (camelCase vs snake_case).
  - Khắc phục lỗi thiếu thư viện `sqlalchemy` và `aiosqlite` khi chuyển đổi giữa các nhánh.

## 3. Cải tiến API & Backend (FastAPI)
- **Mở rộng API:** Sửa đổi endpoint `/search` trong `src/api/routes.py` để hỗ trợ tham số `limit`, tăng giới hạn kết quả mặc định từ 10 lên 20 bài báo mỗi lần tìm kiếm.
- **Tư vấn tích hợp API bên ngoài:** Đã test và tư vấn cách tích hợp thêm nguồn dữ liệu cao cấp từ **Scopus (Elsevier)** và **Web of Science (Clarivate)** dựa trên API Keys người dùng cung cấp. Phân tích chi tiết lỗi 403 của hệ thống WoS.
- **Phân tích thuật toán:** Đọc và giải thích chi tiết thuật toán `LitScore` (đánh giá uy tín bài báo dựa trên số năm xuất bản và tổng số lượt trích dẫn).

## 4. Tư vấn Kiến trúc Dự án (Architecture & MVP Planning)
- Giải thích và làm rõ định hướng công nghệ của Phase 1: Tập trung vào RAG và tích hợp API, không cần tự train model.
- Chia nhỏ và đề xuất kế hoạch làm việc (Task Breakdown) cho nhóm 4 người để hoàn thành bản MVP trong vòng 1 tuần, đảm bảo mỗi thành viên có một không gian làm việc độc lập (UI, PDF Ingestion, LangGraph Agent, DevOps/API).
- **Thiết kế Multi-Agent:** Đề xuất 3 ý tưởng áp dụng kiến trúc Multi-Agent (LangGraph) vào dự án (Tổ đội Viết bài, Tổ đội Trích xuất dữ liệu, Tổ đội Tự động tìm kiếm) nhằm nâng cấp dự án từ một "PDF Chatbot" thông thường lên một "AI Research Assistant" thực thụ.

---
*Tài liệu này được tạo tự động để ghi nhận tiến độ và những đóng góp cốt lõi trong quá trình Pair-Programming giữa người và AI.*
