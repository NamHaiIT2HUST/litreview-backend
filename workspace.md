# Workspace (LitReview Agent)

## 🌟 Tính năng:

1. **Auto-Extraction Matrix (Bóc tách Ma trận PICO tự động) 🚀**
   - *NotebookLM:* Phải prompt rất dài mới ra được 1 cái bảng, nhưng thỉnh thoảng bị vỡ format.
   - *Workspace:* Có 1 tab riêng tên là "Data Extraction". Chọn 10 file PDF, bấm 1 nút, AI tự động quét và điền vào một bảng tính UI các cột: *Đối tượng nghiên cứu, Thuật toán, Độ chính xác, Điểm yếu*. Xuất trực tiếp ra Excel.
2. **Cross-Examination & Conflict Detection (Dò tìm mâu thuẫn chéo)**
   - *NotebookLM:* Hỏi về bài nào trả lời bài đó.
   - *Workspace:* Bạn hỏi: *"Có sự bất đồng nào về thuật toán 1D CNN giữa các tác giả không?"*. Hệ thống sẽ dùng GraphRAG hoặc Multi-Agent để chỉ ra: *"Tác giả A (2022) cho rằng 1D CNN dễ overfit, nhưng Tác giả B (2024) đã giải quyết bằng kỹ thuật X"*.
3. **Contextual PDF Viewer (Đọc PDF thông minh)**
   - Khi Chatbot trích dẫn (cite) một câu, click vào trích dẫn đó sẽ mở file PDF bên cạnh và **highlight vàng (bôi đậm) chính xác dòng chữ đó** trong file PDF gốc. (Cái này NotebookLM làm rất tốt, chúng ta phải làm bằng hoặc hơn).
4. **Auto-Drafting (Khung sườn Literature Review)**
   - Cho phép người dùng nhập 3 Heading (Mở bài, So sánh phương pháp, Kết luận), AI sẽ đọc toàn bộ PDF và tự động viết một bản nháp học thuật dài 2-3 trang kèm trích dẫn (Citation) chuẩn APA/IEEE.

---

## 🛠 Lộ trình Triển khai (Implementation Plan)

### Phase 1: Hoàn thiện tính năng lõi (Mô phỏng NotebookLM)
- [ ] **Tích hợp PDF Viewer:** Sử dụng thư viện `react-pdf` để hiển thị trực quan file PDF ngay trong Workspace thay vì chỉ tải lên.
- [ ] **Làm mịn ChatPanel:** Hoàn thiện UI/UX của khung chat, thêm tính năng Chat History và Markdown formatting.
- [ ] **Trích dẫn (Citation Tracking):** Khi AI sinh ra câu trả lời từ RAG, bắt buộc phải đính kèm nhãn `[Tên bài báo - Trang số X]`.

### Phase 2: Xây dựng các tính năng đột phá (Vượt NotebookLM) 
- [ ] **Tab "Synthesis Matrix":** Viết UI cho bảng dữ liệu (DataGrid). Viết Backend Agent (Prompt engineering + Structured JSON output) để AI đọc 5 bài báo một lúc và điền số liệu vào bảng.
- [ ] **Nút "Generate Insights":** Agent sẽ tự chạy ngầm đọc tất cả các bài, sau đó đẩy ra 3 Bullet points về "Research Gaps" (Khoảng trống nghiên cứu chưa ai làm).

### Phase 3: Tối ưu hoá & Đóng gói (Polish)
- [ ] Khả năng Export đoạn chat và Bảng Matrix sang file Word (.docx) chuẩn format luận văn.
- [ ] Nâng cấp prompt hệ thống để trả lời mang ngữ điệu học thuật chuyên sâu.

## ❓ Open Questions (Cần bạn quyết định)

> [!IMPORTANT]
> 1. **Về tính năng PDF Viewer:** Bạn có muốn làm giao diện chia nửa màn hình (Split-screen) giống NotebookLM không? Nghĩa là bên trái là khung PDF, bên phải là Chatbot?
> 2. **Về Ma trận bóc tách:** Trong giao diện Workspace, chúng ta nên chia thành 2 Sub-tabs: "Chat với AI" và "Bảng bóc tách", hay gộp chung vào màn hình Chat? (Tôi đề xuất tách riêng Tab để nhìn bảng cho rộng rãi).

