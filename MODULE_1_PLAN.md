# Kế hoạch Triển khai: MODULE 1 - EVIDENCE QUANTIFICATION ENGINE

Theo yêu cầu của hệ thống, module này đóng vai trò lõi trong việc lượng hóa và kiểm chứng bằng chứng, đảm bảo nội dung tổng quan do AI sinh ra hoàn toàn trung thực với tài liệu gốc.

## User Review Required
> [!IMPORTANT]
> **Quyết định về Hạ tầng (Infrastructure)**: Việc sử dụng các mô hình NLI (Natural Language Inference) nội bộ yêu cầu tài nguyên tính toán (CPU/GPU). Xin hãy xác nhận backend hiện tại trên AWS EC2 có đủ RAM/VRAM để chạy các mô hình kích thước `base` (khoảng 400MB-1GB bộ nhớ) hay `large` (khoảng 1.5GB-3GB bộ nhớ), hoặc chúng ta sẽ sử dụng inference qua API/Serverless.

> [!CAUTION]
> **Không sửa đổi kiến trúc lõi**: Theo `PROJECT_STANDARDS.md`, LLM gọi để phân rã claim sẽ sử dụng nghiêm ngặt router tập trung `src/services/llm/router.py`. Việc kết hợp NLI sẽ được cô lập ở service mới để không làm vỡ các module có sẵn.

## Open Questions
> [!WARNING]
> 1. **Dataset Đánh giá (Golden Dataset)**: Để benchmark các mô hình NLI một cách công bằng, chúng ta có thể dùng dataset chuẩn như `SciTail` (khoa học), `SNLI`, hay sẽ tự trích xuất thủ công một tập 100-200 câu từ các PDF trong hệ thống của dự án để gán nhãn? (Khuyến nghị tự build một tập nhỏ từ dữ liệu thật của dự án).
> 2. **Ngôn ngữ**: NLI engine chỉ tập trung vào tiếng Anh cho các bài báo (Paper), hay cần xử lý đa ngôn ngữ?

## Đề xuất Các Mô hình NLU/NLI (Candidates)

Để phục vụ cho phần Tầng 2 (NLI Cross-Check), dưới đây là các mô hình được đề xuất để đưa vào quá trình Benchmark:

1. **`MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`** 🌟 *(Khuyến nghị cao nhất)*: Model được train trên nhiều task (NLI, Fact-checking), cân bằng tuyệt vời giữa độ chính xác và tài nguyên, đặc biệt hiệu quả trong việc phát hiện "Hallucination" (ảo giác).
2. **`cross-encoder/nli-deberta-v3-base`**: Rất phổ biến cho bài toán Entailment, điểm benchmark thường cao hơn RoBERTa.
3. **`cross-encoder/nli-deberta-v3-large`**: Chính xác nhất nhưng tương đối nặng. Chỉ nên chọn nếu server có GPU tốt.
4. **`roberta-large-mnli`**: Mô hình tiêu chuẩn, chạy ổn định, độ tin cậy cao.
5. **`typeform/distilbert-base-uncased-mnli`**: Phiên bản thu gọn cực nhẹ, inference cực nhanh. Phù hợp nếu tài nguyên CPU quá hạn hẹp.

## Kế hoạch Benchmark & Đánh giá Model

Để chọn ra mô hình tối ưu, chúng ta sẽ thực hiện 1 vòng Benchmark trước khi tích hợp cứng vào logic hệ thống.

### 1. Chuẩn bị Dữ liệu (Golden Dataset)
- Trích xuất ngẫu nhiên khoảng 100-200 đoạn văn (Paragraphs) từ cơ sở dữ liệu (các bài báo đã parse).
- Dùng LLM sinh ra các Claims với 3 nhãn thủ công (Human-annotated): `Entailment` (Supported), `Neutral` (Weak), `Contradiction` (Hallucinated).

### 2. Các Tiêu chí Đánh giá (Metrics)
- **Độ chính xác phân loại**: Accuracy, F1-Score cho từng class.
- **Tốc độ (Inference Latency)**: Đo thời gian trung bình (ms) để xử lý 1 cặp (Paragraph, Claim).
- **Tài nguyên (Memory Footprint)**: Mức tiêu thụ RAM khi load mô hình.

### 3. Thực thi
- Xây dựng một file script riêng (`benchmark/benchmark_nli_models.py`).
- Chạy inference hàng loạt.
- Tự động xuất kết quả báo cáo (Scorecard) lưu vào file `BENCHMARK_SCORECARD.md` để team xem xét và quyết định model cuối.

---

## Proposed Changes

Mã nguồn mới sẽ tuân thủ tuyệt đối chuẩn kiến trúc hiện tại, gom gọn vào module mới, không sửa đổi code hiện tại.

### Evidence Quantification Engine Component

#### [NEW] `src/services/evidence_engine/claims_decomposer.py`
Sử dụng hàm `ainvoke_with_failover` từ `src/services/llm/` để gọi mô hình (ví dụ `gemini-3.6-flash`), sử dụng cấu trúc `Structured Output` (Pydantic Schema) để bóc tách câu tổng quan thành danh sách các "Atomic Claims" độc lập.

#### [NEW] `src/services/evidence_engine/offset_matcher.py`
Xử lý tầng 1: Đối soát chuỗi tọa độ (Character-offset/Page mapping). Tìm và bóc tách nội dung thô (chunk) từ database (`papers` hoặc bảng tương ứng) để chuẩn bị cho quá trình NLI.

#### [NEW] `src/services/evidence_engine/nli_checker.py`
Xử lý tầng 2: Tích hợp thư viện `transformers` (hỗ trợ load mô hình đã chọn từ Benchmark). Chạy logic suy diễn và quy đổi điểm Entailment/Contradiction thành nhãn `Supported`, `Weak/Neutral`, hoặc `Hallucinated/Contradiction` theo đúng ngưỡng xác suất đề ra.

#### [NEW] `src/services/evidence_engine/metrics_calculator.py`
Thực thi các công thức toán học:
- Tính Faithfulness Score ($F$) = Tỷ lệ % claim đạt `Supported`.
- Tính Citation Precision ($CP$).
- Tính Hallucination Rate ($H$) = $100\% - F$.

#### [NEW] `benchmark/benchmark_nli_models.py`
Script tự động download các model HuggingFace từ list, chạy đánh giá chéo trên tập dữ liệu mẫu và tính toán F1, Latency để ra quyết định chọn model.

## Verification Plan

### Automated Tests
- Viết các unit tests trong `tests/test_evidence_engine/` để kiểm tra độ chính xác của các công thức trong `metrics_calculator.py` với dữ liệu mock.
- Test hàm `claims_decomposer.py` với Mock LLM Client để đảm bảo logic trích xuất hoạt động bình thường, không phụ thuộc vào LLM endpoint thật.

### Manual Verification
- Chạy script `benchmark_nli_models.py` trực tiếp, kiểm tra bảng phân tích kết quả, dung lượng model và tốc độ.
- Kích hoạt quy trình toàn vẹn: sinh thử 1 bài tổng hợp nhỏ (Synthesis), kiểm tra output logs của Engine xem các luồng Decomposition -> Offset Match -> NLI Score -> Metrics hiển thị có chuẩn xác và hợp lý theo luồng đã thiết kế hay không.
