# Hướng dẫn Benchmark RAG Pipeline

Tài liệu này mô tả chi tiết về Benchmark Harness cho RAG pipeline, bao gồm danh sách câu hỏi test set, cấu trúc của script benchmark, cách chạy, đọc kết quả và cách mở rộng sau này.

## 1. Danh sách câu hỏi (Test Set)

Bộ câu hỏi kiểm thử được lưu trữ dưới định dạng JSON tại `benchmark/test_set.json`. Bộ dữ liệu bao gồm 20 câu hỏi kiểu LitQA2 được trích xuất từ tài liệu `Online_BMMSS_ThuyTung.pdf`:

- **10 Câu hỏi Factual (Thực tế)**: Yêu cầu trả lời ngắn gọn, chính xác (ví dụ: tên người, năm, công thức). Đáp án được kiểm tra bằng cách so khớp từ khóa (keyword match).
- **10 Câu hỏi Synthesis (Tổng hợp)**: Yêu cầu tổng hợp thông tin từ nhiều đoạn/trang trong tài liệu. Đáp án được chấm điểm bằng LLM (LLM-as-a-judge) dựa trên các ý chính cần có (expected key points).

*Mẫu cấu trúc một câu hỏi trong test set:*
```json
{
  "id": "f001",
  "question": "Who initially introduced the split feasibility problem (SFP) and in what year?",
  "expected_answer_contains": ["Censor", "Elfving", "1994"],
  "expected_source_file": "Online_BMMSS_ThuyTung.pdf",
  "expected_source_page": 1,
  "type": "factual"
}
```

## 2. Cấu trúc Benchmark Harness

Script chính thực hiện benchmark là `benchmark/run_benchmark.py`. Kịch bản thực hiện quy trình theo các bước sau cho mỗi câu hỏi:

1. **Retrieval**: Gọi `vector_store_service.search_similar_documents` để lấy Top-20 chunks có liên quan. Tính toán **Retrieval Recall** bằng cách kiểm tra xem `expected_source_file` và `expected_source_page` có xuất hiện trong danh sách retrieved chunks hay không.
2. **Generation**: Gọi `rag_service.generate_answer_with_citations` để sinh ra câu trả lời cuối cùng (`answer`) cùng với mảng các trích dẫn (`citations`).
3. **Answer Accuracy**: Đối với câu hỏi Factual, tính toán tỷ lệ độ phủ từ khóa (từ khóa trong `expected_answer_contains` có xuất hiện trong `answer` hay không - case-insensitive).
4. **Citation Precision**: Tính toán tỷ lệ các trích dẫn *được sử dụng thực sự trong câu trả lời* (`cited_in_answer=True`) có nguồn trỏ về đúng `expected_source_file` và `expected_source_page` hay không.
5. **LLM Judge (cho Synthesis)**: Nếu câu hỏi thuộc loại "synthesis", script sẽ gọi một LLM Prompt đặc biệt sử dụng `rag_service.llm` để chấm điểm mức độ bao quát các ý chính. Điểm số từ `0` đến `10`.
6. **Báo cáo**: Kết quả tổng hợp sẽ in ra terminal và ghi nhận chi tiết mỗi câu vào một file CSV (`benchmark/results/benchmark_YYYYMMDD_HHMMSS.csv`). Dòng đầu tiên của CSV ghi lại metadata (như `MIN_RELEVANCE_SCORE`, `MAX_CONTEXT_CHUNKS`).

## 3. Hướng dẫn Chạy Benchmark

Để chạy script đo kiểm, sử dụng lệnh sau từ thư mục gốc của project:

```bash
python benchmark/run_benchmark.py --test-set benchmark/test_set.json
```

**Lưu ý**: Cần đảm bảo rằng các biến môi trường (`.env`) như `OPENAI_API_KEY` hoặc `GEMINI_API_KEY` đã được thiết lập đúng, bởi script sử dụng trực tiếp các Service hiện có trong backend (`rag_service`, `vector_store_service`).

## 4. Cách Đọc Kết Quả

Sau khi chạy xong, terminal sẽ in ra báo cáo tổng kết (Summary):

- **Retrieval Recall**: Tỉ lệ các trang nguồn mong đợi xuất hiện trong Top-20 retrieved chunks.
- **Answer Accuracy**: Tỉ lệ xuất hiện các từ khóa bắt buộc trong câu trả lời (chủ yếu dùng cho Factual).
- **Citation Precision**: Trong số những trích dẫn (citations) mà LLM quyết định đưa vào câu trả lời cuối cùng, có bao nhiêu phần trăm là trích dẫn đúng trang/tài liệu nguồn.
- **LLM Judge Score**: Chỉ áp dụng cho câu hỏi Synthesis, là điểm số trung bình (trên 10) do LLM chấm dựa trên mức độ bao quát các ý chính (`expected_answer_contains`).

Chi tiết hơn, bạn có thể mở file CSV trong thư mục `benchmark/results/` để xem số liệu từng câu hỏi và thông tin báo lỗi (nếu có).

## 5. Thêm Câu Hỏi Mới Sau Này

Để mở rộng bộ test set:
1. Mở file `benchmark/test_set.json`.
2. Thêm object JSON mới theo đúng schema (bao gồm `id`, `question`, `expected_answer_contains` (mảng strings), `expected_source_file`, `expected_source_page`, `type` (`"factual"` hoặc `"synthesis"`)).
3. Nếu bạn muốn expected page bao phủ nhiều trang, có thể thay đổi `expected_source_page` thành một mảng các số nguyên (ví dụ: `[4, 7, 19]`). Code benchmark đã được thiết kế để hỗ trợ kiểm tra cả giá trị đơn lẫn mảng cho field này.
4. Chạy lại lệnh benchmark và so sánh kết quả mới trong thư mục `results/`.
