# Báo cáo Benchmark 3 Mô hình NLI — Module 1 Evidence Quantification Engine

So sánh 3 ứng viên cho tầng Custom Cross-Encoder NLI, cùng huấn luyện trên Google
Colab (T4 GPU) và đánh giá trên 1 dataset 3 nhãn (`supported`/`contradicted`/
`insufficient`, 924 mẫu: 648 train / 138 val / 138 test) sinh từ chính kho PDF
thật của dự án. Xem `scripts/finetune_nli/` cho pipeline đầy đủ (sinh dataset,
notebook train, script này).

## Bảng kết quả cuối cùng (đã sửa 1 bug đo lường — xem mục dưới)

| Model | Base checkpoint | Tham số | Kích thước fp32 (MB) | Train time (s) | Test Accuracy | Test F1-macro | CPU latency avg (ms) | CPU latency p95 (ms) |
|---|---|---|---|---|---|---|---|---|
| **B_small_from_scratch 🏆** | `microsoft/deberta-v3-small` | 141.9M | 549.3 | 112.6 | **92.75%** | **92.74%** | 170.79 | 256.74 |
| C_xsmall_nli_pretrained | `cross-encoder/nli-deberta-v3-xsmall` | 70.8M | 278.2 | 231.9 | 90.58% | 90.72% | 122.75 | 190.13 |
| A_xsmall_from_scratch | `microsoft/deberta-v3-xsmall` | 70.8M | 278.2 | 97.0 | 90.58% | 90.51% | 128.82 | 199.85 |

## ⚠️ Bug phát hiện và đã sửa: dtype fp16 khiến latency CPU đo sai ~17 lần

Lần chạy Colab đầu tiên báo latency A=3960ms, B=4767ms, C=295ms — chênh lệch phi lý
giữa các model cùng kiến trúc/kích thước. Điều tra cho thấy: checkpoint gốc
`microsoft/deberta-v3-xsmall`/`-small` trên HF Hub publish sẵn ở **fp16**, còn
`cross-encoder/nli-deberta-v3-xsmall` publish ở fp32. Notebook không ép
`torch_dtype=torch.float32` khi `from_pretrained()`, nên A/B bị train và lưu lại
ở fp16 một cách ngoài ý muốn — `TrainingArguments(fp16=False)` chỉ tắt AMP
autocast lúc tính toán, **không** đổi dtype gốc của trọng số. Suy luận fp16 trên
CPU (không có Tensor Core như GPU) chậm hơn fp32 hàng chục lần.

**Đã sửa 2 lớp:**
1. Convert 2 checkpoint đã train (A, B) từ fp16 → fp32 (không cần train lại — giá
   trị trọng số giữ nguyên, chỉ đổi cách biểu diễn số, nên **Test Accuracy/F1-macro
   không đổi**, chỉ latency được đo lại đúng).
2. Sửa `scripts/finetune_nli/02_Train_and_Eval_Colab.ipynb` thêm
   `torch_dtype=torch.float32` tường minh, để lần train sau không dính lại bug này.

Latency trong bảng trên là số đã đo lại **trên máy CPU sạch** (không phải ngay
sau khi GPU train xong trên Colab), giống môi trường EC2 sẽ deploy thật.

## Đánh giá chi tiết model được chọn (B) trên toàn bộ tập test thật

Không chỉ tin theo Test Accuracy/F1-macro tổng hợp — đã chạy lại suy luận trên cả
138 mẫu test để kiểm tra model có bị lệch (bias) về 1 nhãn nào không:

| Nhãn thật | Đúng / Tổng | Tỷ lệ |
|---|---|---|
| supported | 43 / 46 | 93.5% |
| contradicted | 40 / 46 | 87.0% |
| insufficient | 45 / 46 | 97.8% |
| **Tổng** | **128 / 138** | **92.75%** |

Phân bố dự đoán: supported=49, contradicted=42, insufficient=47 — cân bằng, khớp
sát với phân bố nhãn thật (46/46/46), **không** collapse về 1 nhãn duy nhất.

**Giới hạn đã biết** (phát hiện qua sanity-check thủ công, không phải từ tập test):
model dự đoán sai cả 3 câu ví dụ tự viết tay bằng văn phong khác dataset train
(ví dụ diễn đạt lại công thức toán bằng cách khác) — model có xu hướng nhạy với
câu ngoài phân phối huấn luyện (out-of-distribution). Đây là hạn chế thật của một
model train trên dataset nhỏ (648 mẫu train), không phải lỗi hệ thống — nên ghi
nhận trong báo cáo, không che giấu.

## Quy tắc chọn model

Ưu tiên **Test F1-macro** (chất lượng phân loại quan trọng nhất cho việc phát
hiện hallucination — hệ thống chấm điểm bằng accuracy đơn thuần có thể đạt điểm
cao chỉ bằng cách luôn đoán nhãn đa số). B cao hơn C/A khoảng 2 điểm % — lớn hơn
ngưỡng 1.5% coi là "sát nhau", nên được chọn thẳng theo F1-macro mà không cần xét
latency. Cả 3 model sau khi sửa bug dtype đều có latency CPU tốt (122-171ms/câu),
nên chênh lệch tốc độ không phải yếu tố loại trừ.

**Lưu ý về độ tin cậy thống kê**: test set 138 mẫu (46/nhãn) cho sai số ước lượng
khoảng ±5% — chênh lệch 2 điểm % giữa 3 model nằm gần biên độ nhiễu này, nên B là
lựa chọn *hợp lý nhất với bằng chứng hiện có*, không phải kết luận tuyệt đối chắc
chắn. Đánh giá chi tiết per-class (mục trên) cho thấy B hoạt động ổn định đều trên
cả 3 nhãn, củng cố thêm cho lựa chọn này.

**Model được chọn: `B_small_from_scratch` (`microsoft/deberta-v3-small`)**
— đã copy vào `models/nli_evidence_v1/`, sẵn sàng tích hợp qua
`src/services/nli_checker.py`.
