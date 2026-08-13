# Đề xuất Ý tưởng Đột phá (Phase 2) cho "Research Setup" và "Search & Verify"

Hai module bạn đã làm ở Phase 1 hiện tại đang giải quyết rất tốt luồng thao tác cơ bản (Nhập cấu hình -> Tìm kiếm -> Lọc Scopus). Tuy nhiên, để sản phẩm mang tính **"Độc bản" (Unique)** và **"Đậm chất AI Agent"**, gây ấn tượng mạnh với Mentor, chúng ta có thể nâng cấp theo định hướng sau:

---

## 1. Module: Research Setup (Cấu hình Nghiên cứu)
*Hiện trạng:* Form nhập tay tĩnh, phụ thuộc nhiều vào trình độ của người dùng (nếu RQ quá chung chung thì kết quả sẽ rất loãng).

### 🌟 Ý tưởng 1: Interactive PICO/PRISMA Co-Pilot (Trợ lý Phỏng vấn)
Thay vì để người dùng tự nghĩ và điền Form tĩnh, hãy biến nó thành một **Cuộc phỏng vấn 3 bước với AI**:
- Người dùng chỉ cần gõ ý tưởng thô: *"Tôi muốn làm đề tài về AI đoán bệnh tim"*.
- AI sẽ tự động phân tích và "chẻ" ý tưởng thành khung chuẩn **PICO** (Population, Intervention, Comparison, Outcome) thường dùng trong y khoa/nghiên cứu.
- AI **tự đề xuất ngược lại** các tiêu chí Inclusion/Exclusion (Ví dụ: *"Tôi khuyên bạn nên loại trừ các bài báo không viết bằng tiếng Anh, và chỉ tập trung vào tín hiệu 1D ECG"*). Người dùng chỉ việc bấm "Approve" (Đồng ý) thay vì phải tự gõ.

### 🌟 Ý tưởng 2: Semantic Concept Graph (Mở rộng từ khóa tự động bằng MeSH)
- Khi nhập từ khóa *"ECG"*, hệ thống tự động sinh ra một mạng lưới từ khóa đồng nghĩa (Concept Graph) như: *"Electrocardiogram", "Arrhythmia", "Heart Rate Variability"*.
- Giao diện có thể hiển thị như một đám mây từ khóa (Tag cloud) có thể click chọn. AI sẽ tự động ghép chúng thành một biểu thức Boolean tối ưu nhất (AND/OR) để truyền cho module Search.

### 🌟 Ý tưởng 3: RQ Auto-Critique (Chấm điểm Câu hỏi Nghiên cứu)
- Tính năng "Validate": AI đọc Form và cảnh báo: *"Câu hỏi của bạn quá rộng, dự kiến sẽ ra >10,000 kết quả. Gợi ý thêm điều kiện về 'Độ chính xác >90%' vào Exclusion criteria để thu hẹp"*.

---

## 2. Module: Search & Verify (Tìm kiếm & Xác minh)
*Hiện trạng:* Tìm kiếm theo từ khóa (Keyword-based) khá truyền thống và lọc tuần tự.

### 🌟 Ý tưởng 4: Autonomous Snowballing Agent (Tác tử "Vết dầu loang")
Đây là kỹ thuật kinh điển trong SLR (Systematic Literature Review) mà chưa tool AI nào làm tử tế:
- Khi tìm được 1-2 bài báo mà người dùng đánh giá là **"Cực kỳ hoàn hảo" (Seed Papers)**.
- Người dùng bấm nút **"Snowball Search"**. Một Agent chạy ngầm sẽ tự động quét:
  1. Toàn bộ các bài báo mà Seed Paper này trích dẫn (Backward snowballing).
  2. Toàn bộ các bài báo mới hơn đã trích dẫn Seed Paper này (Forward snowballing).
- Sau đó Agent tự động mang các bài này đi check Scopus và gạn lọc. Điều này giúp tìm ra những bài nền tảng (Seminal work) mà Google Scholar có thể bỏ sót.

### 🌟 Ý tưởng 5: Double-blind AI Screening (Lọc 2 vòng với Agent)
Để giải quyết bài toán "Ảo giác" (Hallucination) khi AI đọc Abstract bị sai:
- Chúng ta dùng **Multi-Agent Architecture**:
  - **Agent 1 (Reviewer):** Đọc Abstract và ra quyết định (Keep/Reject).
  - **Agent 2 (Supervisor):** Không biết kết quả của Agent 1. Nó nhận Abstract, phản biện lại dựa trên Criteria, và đưa ra quyết định độc lập.
  - Nếu 2 Agent đồng thuận -> Duyệt. Nếu xung đột -> Chuyển sang trạng thái "Needs Human Review" (Đánh dấu màu cam trên UI để bạn tự quyết).
- Mentor sẽ cực kỳ thích kiến trúc Multi-Agent giải quyết xung đột logic này.

### 🌟 Ý tưởng 6: Quality Visualizer (Lọc kết quả bằng Biểu đồ bong bóng)
- Thay vì nhìn 1 list danh sách dài nhàm chán, hiển thị 1 biểu đồ 2D (Trục X: Năm xuất bản, Trục Y: Số lượt trích dẫn, Màu sắc/Kích thước: Điểm phù hợp Semantic do AI chấm).
- Người dùng có thể dùng chuột **"Khoanh vùng" (Lasso)** những cục bong bóng to nhất ở góc trên bên phải (Bài báo mới + Nhiều trích dẫn + Phù hợp nhất) để kéo thả thẳng vào Workspace.

---

## ❓ Lựa chọn của bạn (Open Questions)

> [!IMPORTANT]
> Đây là các "Vũ khí hạng nặng" dành cho Phase 2. Để không bị quá tải, bạn muốn ưu tiên làm **1 tính năng cho Setup** và **1 tính năng cho Search** nào trước?
> 
> **Gợi ý của tôi:**
> 1. Cho **Setup**: Nên làm **Interactive PICO Co-pilot** (Giao diện phỏng vấn AI, tự sinh tiêu chí) vì nó đập ngay vào mắt người dùng sự thông minh khác biệt.
> 2. Cho **Search**: Nên làm **Snowballing Agent** (Tìm vết dầu loang từ 1 bài gốc) hoặc **Double-blind Screening** (2 Agent cãi nhau) vì nó thể hiện rõ tính chất "Tác tử tự chủ" (Agentic).

Bạn thấy ý tưởng nào "bánh cuốn" nhất? Hãy comment ở dưới, nếu ưng ý thì chốt luôn để tôi lập Checklist Task và chiến!
