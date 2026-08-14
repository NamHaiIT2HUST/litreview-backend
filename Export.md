# Tổng quan về Module 6: Export & Citation Hub

Module **Export** đóng vai trò là "Cửa ngõ đầu ra" (Output Gateway) cuối cùng của hệ thống LitReview Agent. Nó có nhiệm vụ kết xuất toàn bộ dữ liệu đã được tìm kiếm, sàng lọc, và tổng hợp thành các định dạng tiêu chuẩn phục vụ cho việc viết bài báo khoa học (SLR).

Dưới đây là danh sách chi tiết những tính năng và tác dụng của màn hình Navigation Export:

## 1. Mục đích và Tác dụng cốt lõi
- **Chuyển đổi Dữ liệu thành Tài liệu Học thuật:** Hệ thống không chỉ lưu dữ liệu dạng thô mà còn format sẵn theo các chuẩn trích dẫn để chèn thẳng vào báo cáo hoặc phần mềm quản lý tài liệu.
- **Tính Minh bạch & Lưu vết (Traceability):** Cho phép người dùng theo dõi lịch sử xuất file, đảm bảo họ có thể lấy lại bản sao lưu bất kỳ lúc nào nếu dữ liệu làm việc bị thất lạc.
- **Tiện ích Preview:** Người dùng có thể xem trước nội dung sẽ tải về ngay trên UI hoặc copy mã (snippet) nhanh gọn thay vì phải tải toàn bộ file.

## 2. Các Lớp Dữ liệu (Data Scopes)
Export Navigation cung cấp 3 lựa chọn về phạm vi dữ liệu:
- **Keep Papers Only (Khuyên dùng):** Chỉ trích xuất những bài báo mà người dùng đã tick chọn thủ công hoặc AI đã quyết định "Keep" sau khi sàng lọc. (Đây là dữ liệu chính hãng 100% chuẩn xác).
- **Synthesis & Workspace Set:** Xuất toàn bộ những bài báo hiện đang có mặt trong không gian làm việc (Workspace).
- **All Project Search Results:** Xuất TOÀN BỘ dữ liệu tìm kiếm được từ ban đầu, bao gồm cả rác, rớt, và đang chờ duyệt (Thích hợp cho việc lưu trữ thô).

## 3. Các Định dạng Hỗ trợ và Tác dụng
Giao diện sẽ hiển thị 4 tùy chọn định dạng xuất file:

| Định dạng | Ý nghĩa & Tác dụng |
| :--- | :--- |
| **BibTeX (.bib)** | **Sử dụng cho:** Mendeley, Zotero, EndNote, LaTeX.<br/>**Tác dụng:** Xuất bộ mã BibTeX chuẩn chứa đầy đủ meta-data (Tác giả, Năm, Tạp chí, DOI). Giúp người dùng click 1 phát import toàn bộ danh sách trích dẫn vào phần mềm viết luận văn. |
| **CSV (.csv)** | **Sử dụng cho:** Excel, Google Sheets.<br/>**Tác dụng:** Xuất dạng bảng lưới (Grid) với các cột tách biệt. Rất cần thiết để nghiên cứu sinh lập Ma trận Tổng quan (Synthesis Matrix), so sánh ưu nhược điểm của các bài báo một cách thủ công. |
| **Markdown (.md)** | **Sử dụng cho:** Notion, Obsidian, GitHub.<br/>**Tác dụng:** Tự động gen ra một bản báo cáo text thô chứa Danh sách tài liệu và một đoạn Bản nháp (Draft) do hệ thống (hoặc người dùng) viết tay, kèm theo trích dẫn chuẩn. |
| **JSON (.json)** | **Sử dụng cho:** Backup dữ liệu, Lập trình viên.<br/>**Tác dụng:** Xuất toàn bộ cục dữ liệu gốc chứa mọi trường thông tin ẩn, để sau này có thể Import ngược lại vào hệ thống hoặc dùng cho script AI khác xử lý tiếp. |

## 4. Các tính năng mở rộng cần hiển thị trên UI
- **Tùy chỉnh nội dung (Customization):**
  - Checkbox: Bao gồm hoặc Không bao gồm Tóm tắt (Abstract) để giảm dung lượng file CSV/BibTeX.
  - Dropdown: Chọn kiểu Key trích dẫn cho BibTeX (vd: *Author2024* hay *Author2024Title*).
- **Live Preview:**
  - Màn hình đen Code Editor hiển thị trực tiếp dữ liệu chuẩn bị tải.
- **Lịch sử Export (History Log):**
  - Lưu lại nhật ký tải file (Giờ tải, Số lượng bài, Tên file) và cho phép bấm tải lại (Re-download) ngay lập tức.
