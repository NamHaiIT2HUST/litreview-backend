# Kế hoạch Triển khai: MODULE 1 - EVIDENCE QUANTIFICATION ENGINE
*(Bản chiến dịch "Làm chủ công nghệ" - HACKATHON 48 GIỜ)*

Nhận định: Yêu cầu **hoàn thành gấp trong 2 ngày** (48 giờ) đòi hỏi một chiến lược thực thi kiểu "Hackathon" - cực kỳ tập trung, loại bỏ rườm rà nhưng **vẫn giữ nguyên bản chất cốt lõi của việc "Làm chủ công nghệ"**. 

Thay vì chu trình R&D kéo dài 4 tuần, chúng ta sẽ áp dụng **Rapid Prototyping & LoRA Fine-Tuning** để có ngay một Kiến trúc 3 tầng (Tri-Layer Hybrid Engine) của riêng dự án với mô hình NLI tự train trong chưa đầy 48 tiếng.

---

## TÍNH KHẢ THI KHI DEPLOY LÊN AWS EC2 HIỆN TẠI

Dựa trên tài liệu `PROJECT_STANDARDS.md` (hệ thống chạy uvicorn trực tiếp, không có worker Celery), việc đưa mô hình AI lên EC2 cần đặc biệt lưu ý:

1. **Về RAM (Memory)**: 
   - Mô hình `deberta-v3-small` (141 triệu tham số) khi load vào PyTorch/HuggingFace sẽ ngốn thêm khoảng **700MB - 1GB RAM**. 
   - Nếu EC2 của bạn là loại **`t3.small` (2GB RAM) hoặc `t3.medium` (4GB RAM)**, hệ thống chạy **thoải mái**. 
   - ⚠️ *Cảnh báo*: Nếu EC2 đang dùng là `t2.micro` (1GB RAM - Free tier), server chắc chắn sẽ bị sập (Out of Memory) vì OS + FastAPI + ChromaDB + Model sẽ vượt quá 1GB. Giải pháp lúc đó là phải ép kiểu (Quantize) mô hình sang định dạng ONNX INT8 (chỉ còn ~200MB).

2. **Về CPU (Nghẽn cổ chai Event Loop)**:
   - Chạy inference `deberta-v3-small` trên CPU mất khoảng 0.1 - 0.2 giây/câu. Tốc độ này hoàn toàn chấp nhận được.
   - Tuy nhiên, do dự án không có Celery Worker mà dùng `BackgroundTasks` trong FastAPI, việc tính toán CPU nặng sẽ chặn (block) toàn bộ server, khiến các user khác bị lag. 
   - **Cách giải quyết bắt buộc khi code**: Phải đưa hàm chạy model vào một luồng riêng bằng `asyncio.to_thread(...)` để không làm "đóng băng" uvicorn.

---

## KIẾN TRÚC ĐỘNG CƠ LƯỢNG HÓA 3 TẦNG (TRI-LAYER HYBRID ENGINE)

### Bước 1: Phân rã Luận điểm (Claims Decomposition)
- Dùng Pydantic Schema + hàm `ainvoke_with_failover` (Gemini-3.6-flash có sẵn) để trích xuất nhanh 1 đoạn văn thành mảng JSON `[{"claim": "..."}]`. (Code: 2 giờ).

### Bước 2: Kênh Kiểm chứng 3 Tầng (Tri-Layer Verification)
#### 📍 Tầng 1: Exact/Fuzzy Matching (Code trong 2 giờ)
- Viết hàm so khớp chuỗi nhanh. Nếu Claim xuất hiện nguyên vẹn $>90\%$ từ vựng trong bản gốc -> `Supported`. Không cần gọi AI.

#### 📍 Tầng 2: Custom Cross-Encoder NLI (Trái tim của dự án)
Đây là phần làm chủ công nghệ, chúng ta tự Fine-tune model của mình.
- **Model Base**: `microsoft/deberta-v3-small` (Rất nhẹ, tối ưu RAM cho EC2).
- **Cách làm nhanh**: Dùng phương pháp **Transfer Learning** trên 1 dataset nhỏ tự sinh thay vì train hàng vạn mẫu. (Lưu ý code chạy bằng `asyncio.to_thread` khi xử lý model trên EC2).

#### 📍 Tầng 3: LLM-as-a-Judge (Dự phòng)
- Đối với các câu điểm Tầng 2 nằm ở mức lửng lơ (0.4 - 0.8), đẩy qua Gemini đánh giá lại và đưa ra lý do (Explainability).

### Bước 3: Toán học lượng hóa (Mathematical Metrics Engine)
Code các công thức:
1. **Faithfulness Score ($F$)**: $\frac{\sum_{i=1}^n I(Status(c_i) == Supported)}{n} \times 100\%$
2. **Citation Precision ($CP$)**: Tỷ lệ trích dẫn trúng đích / Tổng trích dẫn.
3. **Hallucination Rate ($H$)**: $100\% - F$

---

## CHIẾN DỊCH THỰC THI CHỚP NHOÁNG (48-HOUR ROADMAP)

### NGÀY 1: Xây hạ tầng & Chuẩn bị Data
- **Sáng (4h)**: 
  - Hoàn thiện Code Bước 1 (Tách Claim) và Tầng 1 (Fuzzy Matching).
  - Hoàn thiện Code Tầng 3 (LLM-as-a-Judge). Engine chạy thông luồng.
- **Chiều (4h)**: **Xây dựng Dataset độc quyền thần tốc**.
  - Dùng Gemini API chạy song song sinh ra **2,000 cặp câu** `(Đoạn văn, Claim, Label)`.
  - Định dạng thành file `train.jsonl`.

### NGÀY 2: Train Model & Lắp ráp hoàn thiện
- **Sáng (4h)**: **Rapid Fine-Tuning**.
  - Tải `train.jsonl` lên Google Colab (GPU T4 miễn phí).
  - Train model `deberta-v3-small` (mất ~30-45 phút).
  - Export weights (`pytorch_model.bin`) và đưa file này lên server EC2.
- **Chiều (4h)**: **Tích hợp & Tối ưu luồng EC2**.
  - Cài đặt `nli_checker.py`. Áp dụng `asyncio.to_thread` để load model, tránh chết FastAPI.
  - Test End-to-End trên website. Hoàn thành!
