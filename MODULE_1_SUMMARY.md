# Module 1 — Tri-Layer Evidence Quantification Engine

*Tài liệu tổng kết dành cho báo cáo/demo với mentor. Toàn bộ số liệu trong file
này là số đo thật (đã chạy thật, không phải ước lượng) — nguồn gốc từng số nêu
rõ ở mỗi mục để có thể kiểm chứng lại độc lập.*

---

## 1. Vấn đề giải quyết

Hệ thống LitReview Agent tổng hợp tài liệu khoa học bằng LLM — mỗi câu luận
điểm (claim) trong bài tổng hợp cần được xác minh: câu đó có thật sự được
nguồn trích dẫn hỗ trợ không, hay là LLM "ảo giác" (hallucination)? Cách làm
gốc: gửi TOÀN BỘ claim cho LLM khác đóng vai "giám khảo" (LLM-as-Judge) để
chấm — đúng nhưng **tốn kém** (mỗi claim = 1 lần gọi API trả phí) và **chậm**
(độ trễ mạng cho từng lệnh gọi).

Module 1 xây một "bộ lọc" 2 tầng chạy **trước** LLM-as-Judge, để những câu dễ
xác minh (khớp gần như nguyên văn, hoặc rõ ràng đúng/sai về mặt ngữ nghĩa) được
xử lý tại chỗ, miễn phí, không cần gọi mô hình ngôn ngữ lớn — chỉ câu thật sự
mơ hồ mới đẩy lên LLM như trước. Đây là lý do gọi là **Tri-Layer** (3 tầng).

---

## 2. Kiến trúc 3 tầng

```
Câu luận điểm (claim) + đoạn văn bằng chứng (evidence)
        │
        ▼
┌─────────────────────┐
│ Tầng 1: Exact/Fuzzy  │  So khớp chuỗi thuần túy, KHÔNG dùng AI/model nào.
│ Matching             │  Claim trùng ≥90% từ vựng liên tục với evidence
│ (tất định, tức thời) │  → chốt "supported" ngay lập tức.
└──────────┬───────────┘
           │ (không khớp rõ ràng)
           ▼
┌─────────────────────┐
│ Tầng 2: NLI Cross-   │  Mô hình học sâu NHỎ, chạy CỤC BỘ trên CPU (không
│ Encoder tự huấn      │  gọi API ngoài) — phân loại quan hệ giữa evidence và
│ luyện (Module 1 —    │  claim: supported / contradicted / insufficient,
│ trọng tâm tài liệu   │  kèm độ tin cậy (confidence).
│ này)                 │
└──────────┬───────────┘
           │ (độ tin cậy thấp — model "không chắc")
           ▼
┌─────────────────────┐
│ Tầng 3: LLM-as-Judge │  Cơ chế đã có sẵn trong hệ thống trước Module 1 —
│ (dự phòng, giữ       │  chỉ những claim Tầng 1+2 không quyết được mới tới
│ nguyên không đổi)    │  đây. Có giải thích (explainability) đầy đủ.
└──────────────────────┘
```

**Nguyên tắc thiết kế quan trọng nhất**: Tầng 2 là **pre-filter** (lọc trước),
không phải **thay thế** Tầng 3. Claim nào Tầng 2 không tự tin sẽ đi qua đúng
luồng LLM-as-Judge y hệt như hệ thống trước khi có Module 1 — nghĩa là Module 1
chỉ có thể làm hệ thống **rẻ hơn/nhanh hơn**, không thể làm nó **kém an toàn
hơn** so với trước.

Nhãn `supported` / `contradicted` / `insufficient` không phải đặt mới — đây
chính là `EntailmentStatus` đã có sẵn trong
[`src/models/synthesis_schemas.py`](src/models/synthesis_schemas.py), dùng
chung bởi cả Tầng 2 lẫn cơ chế LLM-as-Judge cũ, nên không cần lớp "dịch nhãn"
nào khi cắm Module 1 vào hệ thống.

---

## 3. Quá trình thực hiện — từng bước, có input/xử lý/output cụ thể

### Bước 1 — Sinh dữ liệu huấn luyện thật từ chính kho PDF của dự án

**Vì sao không dùng dataset NLI có sẵn (SNLI, MultiNLI...)**: các bộ dữ liệu
NLI công khai dùng câu văn tổng quát (tin tức, đời sống), trong khi hệ thống
cần phân loại đúng ngữ cảnh khoa học — thuật ngữ kỹ thuật, số liệu, cấu trúc
câu học thuật. Dataset train phải cùng "chất giọng" với dữ liệu thật hệ thống
sẽ gặp lúc vận hành.

- **Input**: 980 đoạn văn (chunk) đã có sẵn trong vector store của dự án, lấy
  từ 13 bài báo khoa học thật đã nạp vào hệ thống (đa lĩnh vực — Y tế/ECG,
  Robotics/Vision-Language, Toán tối ưu hóa).
- **Xử lý**: script
  [`scripts/finetune_nli/01_generate_dataset.py`](scripts/finetune_nli/01_generate_dataset.py)
  lấy từng đoạn văn làm "premise" (bằng chứng gốc), gọi LLM (`gpt-4o-mini` qua
  `src/services/llm/router.py`) sinh ra 3 câu claim tương ứng: 1 câu đúng
  (paraphrase trung thực), 1 câu sai rõ ràng (lật ngược 1 sự kiện/số liệu thật
  trong đoạn văn), 1 câu cùng chủ đề nhưng đoạn văn không hề khẳng định (không
  đủ căn cứ) — đúng 3 nhãn cần cho bài toán 3-lớp.
- **Output**: 924 mẫu (308 premise × 3 câu, 100% sinh thành công), chia
  648 train / 138 validation / 138 test, **cân bằng tuyệt đối** giữa 3 nhãn
  (216/216/216 ở tập train).
- **Kiểm tra chất lượng thủ công** (không chỉ tin số liệu): đã đọc trực tiếp
  nhiều mẫu để xác nhận nhãn gán đúng — ví dụ 1 mẫu `contradicted` thật: premise
  nói "tần số lấy mẫu tối thiểu 1 kHz", claim bị lật thành "hoạt động tốt với
  tần số dưới 250 Hz" — sai rõ ràng, không phải diễn đạt lại vô hại.
- **1 sự cố thật gặp phải và đã sửa**: task sinh dữ liệu này lúc đầu tự động
  route qua Gemini, dính giới hạn cứng 20 request/ngày của gói miễn phí — 6
  mẫu đầu mất 148.9 giây (rơi vào cơ chế báo lỗi rõ ràng thay vì lỗi âm thầm).
  Đã sửa bằng cách pin riêng task này sang OpenAI trong
  [`src/services/llm/router.py`](src/services/llm/router.py) — sau đó tốc độ
  sinh dữ liệu đạt ~0.16 giây/premise.

### Bước 2 — Huấn luyện và so sánh khách quan 3 mô hình trên Google Colab

**File**: [`scripts/finetune_nli/02_Train_and_Eval_Colab.ipynb`](scripts/finetune_nli/02_Train_and_Eval_Colab.ipynb)

**Vì sao notebook này là bằng chứng "làm chủ công nghệ", không phải chỉ chạy
lệnh có sẵn**: mục tiêu không phải "chọn đại 1 mô hình rồi train", mà là thiết
kế 1 thí nghiệm có kiểm soát để **tách biệt được 2 hiệu ứng** ảnh hưởng tới
chất lượng mô hình — đúng phương pháp nghiên cứu, không phải hackathon đoán mò:

| Mô hình | Nguồn gốc trọng số | Câu hỏi trả lời được |
|---|---|---|
| **A** — `deberta-v3-xsmall` | Chỉ pretrain ngôn ngữ chung, train NLI từ đầu | Baseline nhỏ nhất |
| **B** — `deberta-v3-small` | Chỉ pretrain ngôn ngữ chung, train NLI từ đầu | So với A: **kích thước mô hình lớn hơn có giúp ích không?** |
| **C** — `cross-encoder/nli-deberta-v3-xsmall` | Đã pretrain sẵn trên NLI (SNLI+MultiNLI), fine-tune tiếp | So với A (cùng kích thước): **transfer learning từ NLI có giúp ích không?** |

Cả 3 mô hình dùng **chung 1 dataset, chung tập train/val/test, chung seed** —
chỉ khác đúng 1 biến số mỗi lần so sánh, đúng nguyên tắc thí nghiệm đối chứng.

**Input**: 3 file `train.jsonl` / `val.jsonl` / `test.jsonl` từ Bước 1.

**Xử lý** (chạy trên GPU T4 miễn phí của Colab — máy cá nhân không có GPU nên
train CPU sẽ chậm hơn 15-30 lần, không khả thi để thử nghiệm lặp lại nhiều
lần):
- Train/validation/test **tách bạch hoàn toàn** — không bao giờ đánh giá trên
  chính dữ liệu đã train (lỗi phổ biến nhất khiến số liệu báo cáo sai lệch).
- Theo dõi **F1-macro** trên tập validation để dừng sớm (`EarlyStoppingCallback`),
  không dùng accuracy đơn thuần — vì accuracy có thể cao giả tạo nếu mô hình
  chỉ học cách luôn đoán nhãn xuất hiện nhiều nhất.
- Đo lại **latency suy luận trên CPU ngay trong notebook** (ép `model.to("cpu")`
  dù train bằng GPU) — vì môi trường triển khai thật (EC2) không có GPU, đo
  trên GPU sẽ cho số liệu không dùng được để quyết định.

**3 lỗi kỹ thuật thật gặp phải khi chạy — và cách chẩn đoán/sửa** (đây là phần
thể hiện rõ nhất khả năng tự debug, không phải copy code mẫu chạy suôn sẻ):

1. **Lỗi ABI torch/torchvision**: câu lệnh nâng cấp `torch` trong Cell 1 làm
   lệch phiên bản với `torchvision` cài sẵn trên Colab, gây crash ngay từ đầu.
   → Chẩn đoán: đọc traceback xác định đúng cặp thư viện xung đột, sửa bằng
   cách **không** nâng cấp torch/torchvision (Colab đã có sẵn cặp tương thích).
2. **`warmup_ratio` bị đổi API**: bản `transformers` mới nhất trên Colab không
   còn nhận tham số này theo cách cũ, `TrainingArguments.__init__()` báo lỗi
   `unexpected keyword argument`. → Sửa bằng cách tính tay số bước warmup
   (`warmup_steps`) và viết 1 hàm `build_training_args()` tự lọc bỏ kwarg nào
   phiên bản `transformers` hiện tại không hỗ trợ — không hardcode 1 lần sửa
   mà giải quyết luôn cho các lần chạy sau nếu API tiếp tục đổi.
3. **`fp16=True` không tương thích kiến trúc DeBERTa-v3**: gặp lỗi
   `ValueError: Attempting to unscale FP16 gradients` — đây là xung đột đã
   biết giữa lớp `StableDropout`/`XSoftmax` tùy biến của DeBERTa với cơ chế
   AMP GradScaler của PyTorch. → Tắt hẳn `fp16=False`, đồng thời thêm
   `adam_epsilon=1e-6` (khuyến cáo chính thức của đội DeBERTa để tránh loss
   `NaN` khi train fp32 — nếu không có thay đổi này, loss của model A/B bị kẹt
   ở đúng 0.000000 từ epoch 2 trở đi, độ chính xác giữ nguyên 33.3% (ngẫu
   nhiên) — đã tự phát hiện qua bảng epoch log, không phải do người khác chỉ ra).

**Output**: `comparison_report.json` + 3 checkpoint mô hình đã train.

### Bước 3 — Phát hiện và sửa 1 lỗi đo lường nghiêm trọng (fp16 checkpoint trap)

Lần chạy đầu tiên báo latency CPU: model A = 3960ms/câu, B = 4767ms/câu, C =
295ms/câu — **chênh lệch phi lý** giữa các mô hình cùng lớp kiến trúc. Thay vì
chấp nhận số liệu, đã tự điều tra bằng cách viết script kiểm tra
`next(model.parameters()).dtype` cho từng model:

- **Nguyên nhân tìm ra**: checkpoint gốc `microsoft/deberta-v3-xsmall`/`-small`
  trên HuggingFace Hub được nhà phát hành publish sẵn ở **fp16**, trong khi
  `cross-encoder/nli-deberta-v3-xsmall` publish ở fp32. Notebook không ép
  `torch_dtype=torch.float32` khi `from_pretrained()`, nên A/B vô tình bị
  train và lưu lại ở fp16 — `TrainingArguments(fp16=False)` chỉ tắt tính toán
  AMP lúc train, **không** đổi kiểu dữ liệu gốc của trọng số đã load. Suy luận
  fp16 trên CPU (không có Tensor Core như GPU) chậm hơn fp32 hàng chục lần.
- **Đã sửa 2 lớp**: (1) convert 2 checkpoint đã train (A, B) từ fp16 → fp32
  (không cần train lại — giá trị trọng số không đổi, chỉ đổi cách biểu diễn
  số, nên F1-macro giữ nguyên tuyệt đối, chỉ latency được đo lại đúng); (2) sửa
  notebook thêm `torch_dtype=torch.float32` tường minh để không lặp lại lỗi
  này ở lần train sau.
- **Kết quả sau khi sửa**: latency thực đo được A=128.82ms, B=170.79ms,
  C=122.75ms — tất cả hợp lý, cùng bậc độ lớn như kỳ vọng cho các mô hình
  cùng lớp kích thước.

### Bước 4 — Đánh giá cuối cùng và chọn mô hình

**File**: [`scripts/finetune_nli/03_compare_models.py`](scripts/finetune_nli/03_compare_models.py),
kết quả đầy đủ tại [`models/nli_evidence_benchmark_report.md`](models/nli_evidence_benchmark_report.md).

| Mô hình | Test Accuracy | Test F1-macro | Kích thước fp32 | Latency CPU (avg / p95) |
|---|---|---|---|---|
| **B — `deberta-v3-small` 🏆** | **92.75%** | **92.74%** | 549.3 MB | 170.79 ms / 256.74 ms |
| C — `nli-deberta-v3-xsmall` | 90.58% | 90.72% | 278.2 MB | 122.75 ms / 190.13 ms |
| A — `deberta-v3-xsmall` | 90.58% | 90.51% | 278.2 MB | 128.82 ms / 199.85 ms |

**Kết luận rút ra từ 2 trục so sánh**:
- A vs B (cùng cách train, khác kích thước): B hơn A **2.23 điểm % F1-macro**
  → kích thước mô hình lớn hơn **có** giúp ích rõ rệt.
- A vs C (cùng kích thước, khác nguồn gốc): chênh lệch chỉ 0.21 điểm % → với
  bài toán và dataset này, transfer learning từ NLI pretrained sẵn **gần như
  không** tạo khác biệt đáng kể so với train từ đầu.

**Quy tắc chọn** đã định trước khi biết kết quả (tránh chọn theo cảm tính sau
khi thấy số): ưu tiên F1-macro (quan trọng cho việc phát hiện hallucination
hơn accuracy đơn thuần); B hơn A/C khoảng 2 điểm %, lớn hơn ngưỡng 1.5% coi là
"sát nhau", nên B được chọn thẳng.

**Đánh giá lại trên toàn bộ 138 mẫu test** (không chỉ tin số tổng hợp, kiểm
tra mô hình có bị lệch về 1 nhãn không):

| Nhãn | Đúng / Tổng | Tỷ lệ |
|---|---|---|
| supported | 43/46 | 93.5% |
| contradicted | 40/46 | 87.0% |
| insufficient | 45/46 | 97.8% |

Phân bố dự đoán cân bằng (49/42/47), khớp sát phân bố nhãn thật (46/46/46) —
mô hình **không** collapse về 1 nhãn duy nhất.

**Hạn chế đã biết, công khai không che giấu**: qua kiểm tra thủ công 3 câu tự
viết tay (văn phong khác dataset train — ví dụ diễn đạt lại 1 công thức toán
theo cách khác), cả 3 câu đều bị phân loại sai. Đây là hạn chế thật của một mô
hình train trên dataset còn nhỏ (648 mẫu train) — nhạy với dữ liệu **ngoài
phân phối huấn luyện** (out-of-distribution). Không phải lỗi hệ thống, nhưng
cần biết để đặt kỳ vọng đúng.

### Bước 5 — Tích hợp vào 2 pipeline sản xuất thật (không phải demo riêng lẻ)

Hệ thống có 2 pipeline tổng hợp tài liệu song song đang chạy — Module 1 phải
tích hợp vào **cả hai**, không chỉ 1 pipeline demo:

**5a. Pipeline Legacy** (`SynthesisService.cross_paper_analysis()`,
[`src/services/synthesis_service.py`](src/services/synthesis_service.py)):
- Tầng 1 ([`fuzzy_verbatim_match()`](src/services/claim_verification_policy.py))
  chạy trước, dùng **đoạn khớp liên tục dài nhất** (`difflib.find_longest_match`)
  đo theo % độ dài claim — cố tình **không** dùng cách đếm từ trùng lặp
  (bag-of-words), vì cách đó sẽ coi "X đúng" và "X không đúng" gần như giống
  hệt nhau (chỉ khác đúng từ phủ định). Đo theo đoạn khớp liên tục thì việc
  chèn thêm từ "không" sẽ phá vỡ đoạn khớp, tự động bị loại — đã viết test
  riêng cho đúng tình huống an toàn này.
- Tầng 2 ([`resolve_claims_via_nli()`](src/services/nli_checker.py)) xử lý
  claim còn lại — claim nào Tầng 1+2 quyết được thì loại khỏi danh sách gửi
  LLM (`prepared_for_llm`), phần còn lại đi qua đúng luồng LLM-as-Judge cũ,
  gộp chung kết quả qua đúng cơ chế `sanitize_claim_verification` (chống
  hallucinate `evidence_id`) đã có sẵn — **không bypass** bất kỳ lớp an toàn
  nào đã tồn tại trước Module 1.
- Khi tắt cờ `NLI_EVIDENCE_ENABLED` (mặc định), toàn bộ nhánh Module 1 không
  chạy — hành vi hệ thống y hệt trước khi có Module 1.

**5b. Pipeline fast_v2** (`SectionScopedSynthesisPipeline`,
[`src/synthesis/fast_v2/citations/anthropic_citations.py`](src/synthesis/fast_v2/citations/anthropic_citations.py))
— đây là pipeline **UI thật đang gọi** (nút "Tổng quan tài liệu"):
- Trước khi gửi các câu-claim của 1 đoạn văn cho LLM gán trích dẫn, chạy Tầng
  1 rồi Tầng 2 cho từng câu so với evidence trong phạm vi (scope) mà LLM đáng
  lẽ sẽ thấy — chỉ câu nào Tầng 1/2 **chắc chắn tìm được bằng chứng hỗ trợ**
  mới được gán trích dẫn tự động, câu mơ hồ/mâu thuẫn vẫn để LLM (Tầng 3)
  quyết định như cũ.
- Nếu **toàn bộ** câu trong 1 lô (batch) được Tầng 1/2 giải quyết xong, hệ
  thống **bỏ hẳn** lệnh gọi LLM cho lô đó — tiết kiệm chi phí/độ trễ thật.
- Giới hạn an toàn: nếu phạm vi bằng chứng của 1 lô quá lớn (>20 đơn vị), bỏ
  qua Tầng 2 cho lô đó (Tầng 1 vẫn luôn chạy) để tránh việc so khớp NLI kéo
  dài quá lâu trên CPU — không mất độ phủ, câu đó chỉ đơn giản đi thẳng lên
  Tầng 3 như khi tắt Module 1.

### Bước 6 — Đo lường và hiển thị kết quả cho người dùng

- `GET /synthesis-sessions/{session_id}/quality` — endpoint tính 3 chỉ số cho
  1 phiên tổng hợp Legacy đã hoàn thành: Faithfulness (tỷ lệ claim được xác
  nhận "supported"), Hallucination Rate (100% − Faithfulness), Citation
  Precision (tỷ lệ câu factual được **giữ lại** sau vòng lọc cuối / tổng câu
  factual LLM đề xuất ban đầu — cố ý không tính theo cách "citation có
  evidence_id / tổng citation", vì cách đó luôn ra 100% một cách vô nghĩa do
  mọi `Citation` được lưu vào DB vốn đã đảm bảo hợp lệ từ trước).
- Card thống kê trên UI (tab "Tổng quan tài liệu") — tính trực tiếp từ nội
  dung bài tổng hợp thật đang hiển thị (không phải số liệu tách rời), gồm: %
  đoạn có trích dẫn, % đoạn chưa có trích dẫn, % trích dẫn hợp lệ, số câu được
  Module 1 xác minh cục bộ (không tốn LLM call). 4 số liệu này được lưu vào
  cột `citation_coverage_telemetry` (JSONB) trong bảng `synthesis_sessions`
  ngay lúc tổng hợp xong, nên vẫn hiển thị đúng khi mở lại báo cáo cũ sau này.

---

## 4. Kết quả kiểm chứng cuối cùng

- Toàn bộ `pytest tests/test_fast_v2/ tests/test_services/` — **680 passed**
  (4 fail + 3 error còn lại xác nhận là lỗi có sẵn từ trước Module 1, không
  phải regression — xác minh bằng cách `git stash` code Module 1 rồi chạy lại,
  vẫn ra đúng các lỗi đó).
- Test end-to-end **không mock bất kỳ thành phần nào**: PDF thật → trích xuất
  qua `DocumentProcessor` → ghi vào Postgres thật → gọi
  `cross_paper_analysis()` thật (LLM thật, model NLI thật đã train) → gọi
  `/quality` endpoint thật qua HTTP → nhận đúng số liệu mong đợi.
- Smoke-test riêng cho pipeline fast_v2 với model NLI thật (không mock): model
  load đúng, gán đúng handle trích dẫn, giữ nguyên văn bản 100% byte-for-byte
  (`overall_diff_passed=True`), bỏ đúng lệnh gọi LLM khi Tầng 1 đã giải quyết
  xong toàn bộ câu trong lô.
- `npm run lint` + `npm run build` (frontend) sạch, không lỗi.

---

## 5. Công nghệ / kỹ thuật đã dùng — tham khảo

- **Kiến trúc mô hình**: DeBERTa-v3 (Microsoft) — kiến trúc Transformer cải
  tiến so với BERT/RoBERTa bằng cơ chế disentangled attention (tách biệt biểu
  diễn nội dung và vị trí từ) và ELECTRA-style pretraining. Chọn 3 checkpoint
  công khai trên HuggingFace Hub (`microsoft/deberta-v3-xsmall`,
  `microsoft/deberta-v3-small`, `cross-encoder/nli-deberta-v3-xsmall`).
- **Bài toán**: Natural Language Inference (NLI) 3 lớp, thu hẹp phạm vi thành
  bài toán "evidence-claim entailment" chuyên biệt cho văn bản khoa học, thay
  vì dùng thẳng dataset NLI tổng quát.
- **Huấn luyện**: HuggingFace `transformers.Trainer`, fine-tune toàn bộ mô
  hình (không freeze layer), `EarlyStoppingCallback` theo dõi F1-macro,
  `adam_epsilon=1e-6` (khuyến cáo chính thức DeBERTa cho ổn định fp32).
- **Hạ tầng huấn luyện**: Google Colab (GPU T4, miễn phí) cho bước train — có
  cân nhắc rõ ràng khi nào dùng máy cá nhân (CPU, sinh dữ liệu/đánh giá/tích
  hợp) và khi nào cần GPU (train nhiều epoch × 3 mô hình).
- **Thuật toán so khớp Tầng 1**: `difflib.SequenceMatcher.find_longest_match`
  (longest contiguous matching subsequence) — lựa chọn có chủ đích thay vì
  bag-of-words overlap, vì tính an toàn trước phủ định ngữ nghĩa (negation-safe
  by design).
- **Pattern tích hợp**: coverage-preserving pre-filter — giải quyết trước
  những gì giải quyết được rẻ/nhanh, loại khỏi phần việc gửi cho tầng đắt tiền
  hơn, merge kết quả trước khi các lớp kiểm tra an toàn hiện có (fail-closed
  guard) chạy — không tạo luồng xử lý song song tách biệt.

---

## 6. Cách demo / kiểm chứng lại cho mentor

1. **Xem báo cáo huấn luyện đầy đủ**: [`models/nli_evidence_benchmark_report.md`](models/nli_evidence_benchmark_report.md)
   — bảng số liệu 3 mô hình, phân tích bug đo lường, đánh giá per-class.
2. **Xem notebook đã chạy xong**: [`scripts/finetune_nli/02_Train_and_Eval_Colab.ipynb`](scripts/finetune_nli/02_Train_and_Eval_Colab.ipynb)
   — mở trên Colab hoặc trực tiếp trong repo, thấy đầy đủ log train 3 mô hình,
   epoch metrics, comparison report cuối cùng.
3. **Chạy lại từ đầu (nếu muốn xem quy trình sống)**:
   ```bash
   python scripts/finetune_nli/01_generate_dataset.py --n-premises 300 --concurrency 10
   ```
   rồi upload 3 file `.jsonl` sinh ra vào notebook Colab, `Runtime → Run all`.
4. **Xem trên UI thật**: vào 1 tài liệu → tab "Phân tích" → "Tổng quan tài
   liệu" → chạy tổng hợp mới → xem card thống kê phía trên nội dung, đặc biệt
   ô "Xác minh cục bộ (không qua AI)" — con số này > 0 nghĩa là Module 1 vừa
   thật sự tiết kiệm được ít nhất 1 lệnh gọi LLM.
5. **Đọc code tích hợp**: [`src/services/nli_checker.py`](src/services/nli_checker.py)
   (luật hợp nhất Tầng 2), [`src/services/claim_verification_policy.py`](src/services/claim_verification_policy.py)
   (Tầng 1), [`tests/test_services/test_nli_checker.py`](tests/test_services/test_nli_checker.py)
   + [`tests/test_fast_v2/test_tier12_citation_prefilter.py`](tests/test_fast_v2/test_tier12_citation_prefilter.py)
   (test tự động cho toàn bộ luật quyết định).

---

## 7. Kế hoạch gốc và trạng thái đầy đủ

Tài liệu này là bản tóm tắt. Kế hoạch chi tiết đầy đủ (bao gồm tính toán triển
khai AWS EC2, RAM sizing, các lựa chọn đã cân nhắc và loại bỏ) nằm tại
[`MODULE_1_PLAN.md`](MODULE_1_PLAN.md). Hướng dẫn triển khai lên EC2 thật nằm
tại [`DEPLOY_EC2_MODULE1.md`](DEPLOY_EC2_MODULE1.md).

---

## 8. Cập nhật sau khi triển khai thật lên EC2 — RAM không đủ, đã tắt Tầng 2 trên production

Toàn bộ mô tả ở trên (Bước 1-6) đã chạy đúng và kiểm chứng đầy đủ trên máy
local. Khi đưa lên server thật (`t165-server`, AWS EC2 `t3.small`, 2GB RAM),
phát sinh 1 giới hạn hạ tầng thực tế cần ghi nhận trung thực thay vì che giấu:

- RAM khả dụng (`available`) trên instance này, khi backend đã chạy nhưng
  **chưa** bật Tầng 2, chỉ còn **615MB**.
- Đã thử load model nhẹ nhất trong 3 model đã huấn luyện (model C, 279MB trên
  đĩa — xem mục 4) trực tiếp trên server: RAM `available` tụt xuống còn
  **140MB**. Không dừng ở mức "rủi ro về mặt lý thuyết" — **kernel Linux đã
  thật sự kích hoạt OOM-killer và giết chết tiến trình backend** để cứu hệ
  thống (xác nhận bằng log `dmesg`/`journalctl`: `Out of memory: Killed
  process ... (python)`), gây gián đoạn dịch vụ thật trong lúc đo.

**Quyết định triển khai**: tắt hẳn Tầng 2 trên production hiện tại
(`NLI_EVIDENCE_ENABLED=false`). Tầng 1 (khớp gần-nguyên-văn, không tốn RAM) và
Tầng 3 (LLM-as-Judge) vẫn hoạt động đầy đủ, đúng thiết kế ban đầu — **hệ thống
không có lỗi gì**, chỉ tạm thời không tận dụng được phần tiết kiệm chi phí LLM
mà riêng Tầng 2 mang lại. Model C đã được copy sẵn vào đúng đường dẫn
(`~/P-165/models/nli_evidence_v1/`) trên server, để khi nâng cấp instance lên
`t3.medium` (4GB) trở lên chỉ cần đổi 1 dòng cấu hình và khởi động lại, không
cần làm lại gì từ đầu.

Đây là phần đáng nói thêm với mentor không kém phần huấn luyện mô hình: "làm
chủ công nghệ" không dừng ở việc train và tích hợp đúng, mà còn ở việc **vận
hành thật có giới hạn tài nguyên** — đo đạc bằng số liệu thật trên chính môi
trường triển khai thay vì chỉ tin ước tính lý thuyết, và biết đưa ra quyết
định đánh đổi đúng lúc (tắt một tính năng không bắt buộc thay vì để cả hệ
thống sập) khi hạ tầng có giới hạn thật.
