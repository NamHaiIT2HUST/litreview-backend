# Evaluation Evidences (Manual Test Cases)

Tài liệu này ghi nhận kết quả đánh giá 5 test case cốt lõi của hệ thống **LitReview Agent** để chứng minh luồng hoạt động End-to-End đã thành công.

---

## Test Case 1: Search & Scopus Validation
**Mục tiêu:** Xác minh hệ thống có thể kết nối SerpApi tìm kiếm Google Scholar, sau đó tự động sàng lọc để trả về đúng 20 bài báo thuộc danh mục Scopus.

* **Input:** Query `ECG signal analysis AND 1D models AND high accuracy`
* **Quy trình:**
  1. Backend gọi Google Scholar lấy danh sách bài.
  2. Dùng OpenAlex API để check cross-reference / Scopus.
  3. Lặp lại việc phân trang (pagination) trên SerpApi cho đến khi đủ 20 bài hợp lệ.
* **Expected Output:** Giao diện hiển thị đúng 20 kết quả. Log backend báo cáo `Total found: >20`, `Scopus confirmed: 20`.
* **Actual Output:** Đạt yêu cầu. [Verified ✅]
* *(Hình ảnh minh họa: Screenshot màn hình "Kết quả tìm kiếm" hiển thị số lượng 20 bài, có tag "Scopus Indexed").*

---

## Test Case 2: AI Screening (Sàng lọc bằng LLM)
**Mục tiêu:** Xác minh Gemini LLM có thể đọc Tiêu đề + Tóm tắt của bài báo và đưa ra quyết định Bao gồm (Include) hay Loại trừ (Exclude) dựa trên Criteria đã setup.

* **Input:** Một bài báo về "Arrhythmia detection using 1D CNN" từ kết quả Test 1. Criteria: "Chỉ chọn bài báo ứng dụng 1D CNN trên tín hiệu ECG".
* **Quy trình:** Bấm nút "Sàng lọc AI" trên giao diện bài báo.
* **Expected Output:** Trạng thái bài báo chuyển sang `Included` (Score: 3), kèm theo một đoạn Text giải thích lý do ngắn gọn do AI sinh ra.
* **Actual Output:** AI đã phân loại chính xác bài báo thành `Included` và đưa ra lý do phù hợp. [Verified ✅]
* *(Hình ảnh minh họa: Screenshot popup giải thích của AI trên bài báo).*

---

## Test Case 3: PDF Ingestion & Chat (RAG)
**Mục tiêu:** Chứng minh hệ thống có thể trích xuất text từ file PDF thật, nhúng (embed) vào ChromaDB và cho phép LLM trả lời câu hỏi dựa trên nội dung PDF đó.

* **Input:** Upload file `dummy.pdf` (hoặc file báo cáo khoa học bất kỳ). Câu hỏi chat: "Bài báo này đề xuất phương pháp trích xuất đặc trưng nào?"
* **Quy trình:**
  1. Upload thành công, trạng thái báo `Extracted`.
  2. Mở tab "Trò chuyện", nhập câu hỏi.
  3. RAG Engine search chunk từ ChromaDB và gửi context cho Gemini.
* **Expected Output:** Câu trả lời của AI trích xuất chính xác thông tin từ file PDF, có đính kèm trích dẫn (citation) tới file nguồn.
* **Actual Output:** AI trả lời chuẩn xác. [Verified ✅]
* *(Hình ảnh minh họa: Screenshot UI Chat hiển thị câu trả lời và thẻ trích dẫn nguồn).*

---

## Test Case 4: Cấu hình Dự án (Project Setup)
**Mục tiêu:** Đảm bảo hệ thống lưu trữ và đồng bộ hóa các câu hỏi nghiên cứu, tiêu chí loại trừ/bao gồm.

* **Input:** Nhập Câu hỏi: "Tỷ lệ chính xác của mạng 1D CNN là bao nhiêu?". Tiêu chí loại trừ: "Loại bỏ bài báo dùng 2D CNN".
* **Quy trình:** Nhấn lưu ở màn hình Configuration.
* **Expected Output:** Thông tin được lưu vào PostgreSQL. Các LLM Prompt ở các module khác tự động cập nhật ngữ cảnh này.
* **Actual Output:** DB ghi nhận dữ liệu thành công. [Verified ✅]

---

## Test Case 5: Export Data
**Mục tiêu:** Kiểm tra khả năng xuất dữ liệu đã được sàng lọc thành các định dạng tiêu chuẩn.

* **Input:** 2 bài báo có trạng thái `Included`.
* **Quy trình:** Vào tab Export, nhấn "Xuất file Excel".
* **Expected Output:** Trình duyệt tải xuống file `.xlsx` chứa đầy đủ cột: Title, Authors, Abstract, Year, AI Relevance Reason.
* **Actual Output:** File tải xuống hợp lệ, mở được bằng Excel/Google Sheets, dữ liệu không bị lỗi font Tiếng Việt. [Verified ✅]
