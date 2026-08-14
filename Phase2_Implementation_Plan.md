# Kế hoạch Triển khai Kiến trúc Multi-Agent & Fine-Tuning (Phase 2)

Dựa trên yêu cầu của bạn về việc muốn hệ thống đi sâu vào xu hướng **AI Agent / Multi-Agent** và **Fine-Tuning**, tôi đề xuất một kiến trúc hạng nặng, biến hệ thống từ một "công cụ hỗ trợ" thành một "Tổ đội Nghiên cứu sinh Ảo" (Virtual Research Team) hoạt động độc lập.

Dưới đây là 3 ý tưởng cụ thể để áp dụng cho 2 module "Research Setup" và "Search & Verify":

---

## 1. Multi-Agent Debate System (Hệ thống Tác tử Biện luận) cho Research Setup

Thay vì chỉ dùng 1 prompt để bảo AI tạo ra tiêu chí tìm kiếm, chúng ta sẽ xây dựng một **Tổ đội 3 Agents** cùng "họp" để tối ưu hóa đề tài của bạn.

*   **Kiến trúc Multi-Agent:**
    *   🧑‍⚕️ **Agent 1 (Domain Expert):** Đóng vai trò chuyên gia trong ngành (vd: Bác sĩ tim mạch). Nhiệm vụ: Đánh giá tính thực tiễn và tính mới của câu hỏi nghiên cứu.
    *   📊 **Agent 2 (PRISMA Methodologist):** Chuyên gia phương pháp luận. Nhiệm vụ: Ép câu hỏi của người dùng vào chuẩn PICO (Population, Intervention, Comparison, Outcome) và đề xuất các tiêu chí Inclusion/Exclusion cực kỳ khắt khe.
    *   🔍 **Agent 3 (Librarian):** Chuyên gia thủ thư. Nhiệm vụ: Xây dựng các cụm từ khóa Boolean (AND/OR) tối ưu nhất để vét cạn Google Scholar mà không bị nhiễu.
*   **Luồng hoạt động (Workflow):** Bạn chỉ cần nhập 1 câu ý tưởng. 3 Agents này sẽ tự động "chat" với nhau ngầm ở backend (hoặc hiện text streaming cho bạn xem). Sau 3 vòng tranh luận, chúng sẽ tổng hợp ra một bản Cấu hình Nghiên cứu (Research Setup) hoàn hảo nhất để bạn duyệt.

---

## 2. Autonomous "Spider" Swarm (Bầy đàn Tác tử Thu thập) cho Search & Verify

Việc lấy dữ liệu từ Google Scholar hiện tại bị giới hạn bởi API (thường chỉ lấy được 20-100 bài và dễ thiếu PDF). Chúng ta sẽ thay bằng một **Bầy đàn Agents (Swarm)**.

*   **Kiến trúc Multi-Agent:**
    *   **Agent A (Query Expander):** Tự động sinh ra 5-10 biến thể của chuỗi Boolean từ khóa và đem đi search song song.
    *   **Agent B (PDF Hunter):** Nhận link DOI từ Agent A, tự động đi lùng sục file PDF Full-text từ các nguồn mở (Unpaywall, arXiv, Core.ac.uk) hoặc dùng kỹ thuật scraping thông minh để lấy nội dung.
    *   **Agent C (Fact-Checker):** Đối chiếu ngay lập tức với API của Scopus/SJR để dán nhãn Q1/Q2/Q3/Q4.
*   **Điểm đột phá:** Các tác tử này chạy bất đồng bộ (Asynchronous) trong nền (Background worker). Bạn bấm "Search", tắt máy đi ngủ, bầy đàn Agent sẽ tự bò đi cào hàng ngàn bài báo và nhặt PDF về Workspace cho bạn.

---

## 3. Áp dụng Fine-Tuning Model chuyên biệt (The "Devil's Advocate")

Việc dùng GPT-4o hay Gemini Pro để đánh giá (Screening) hàng ngàn bài báo sẽ **rất tốn kém chi phí API và chậm**. Đây là lúc Fine-Tuning phát huy tác dụng.

*   **Huấn luyện Model chuyên biệt (Fine-Tuning):**
    *   Chúng ta sẽ thu thập khoảng 5,000 - 10,000 cặp dữ liệu (Abstract + Tiêu chí Inclusion/Exclusion -> Kết quả: Giữ hay Bỏ).
    *   Dùng dữ liệu này để **Fine-tune một mô hình mã nguồn mở nhỏ gọn** (như Llama-3-8B hoặc Gemma-2B).
    *   Mô hình này sẽ được deploy nội bộ (hoặc trên server rẻ). Nó cực kỳ giỏi và siêu tốc trong ĐÚNG MỘT VIỆC: Đọc Abstract và phán đoán xem bài báo này có vi phạm Exclusion Criteria hay không.
*   **Multi-Agent Screening (Lọc mù đôi):**
    *   Mô hình Fine-tune (Nhỏ, rẻ, nhanh) sẽ quét qua 10,000 bài báo để loại bỏ 9,000 bài rác (Agent 1).
    *   GPT-4o (Lớn, đắt, thông minh - Agent 2) sẽ đóng vai trò "Devil's Advocate" (Kẻ đóng vai ác), chỉ đọc lại 1,000 bài đã qua vòng 1 để tìm ra lý do loại trừ tinh vi hơn (vd: "Bài này tuy nói về ECG nhưng phương pháp là 2D CNN chứ không phải 1D").
    *   **Kết quả:** Tiết kiệm 90% chi phí API nhưng độ chính xác lại tiệm cận con người.

---

## Lựa chọn của bạn

Các hướng đi trên đều tập trung mạnh vào năng lực AI Agent. Bạn hãy quyết định xem tính năng nào sẽ là **"Killer Feature"** mà bạn muốn làm đầu tiên cho Phase 2!
