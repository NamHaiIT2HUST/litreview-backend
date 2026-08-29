# Kế hoạch Triển khai: MODULE 1 — EVIDENCE QUANTIFICATION ENGINE (v2)

*Bản thiết kế lại, thay thế bản "Hackathon 48 giờ" trước đó. Giữ nguyên ý tưởng kiến
trúc gốc (Tri-Layer Hybrid Engine) nhưng thiết kế lại phần huấn luyện model cho
đúng phương pháp (train/val/test tách bạch, 3 model so sánh trên cùng 1 dataset,
số liệu đo thật thay vì ước lượng), và tính toán kỹ phần triển khai lên AWS EC2.*

> **✅ HOÀN TẤT (2026-08-28)**: Đã sinh dataset thật (924 mẫu), train + so sánh
> đầy đủ 3 model trên Colab, phát hiện và sửa 1 bug đo lường latency nghiêm trọng
> (dtype fp16 ngoài ý muốn), đánh giá lại model được chọn trên toàn bộ tập test,
> copy vào `models/nli_evidence_v1/`. Xem mục 8 để biết chi tiết từng bước và mục
> "KẾT QUẢ CUỐI CÙNG" ngay dưới đây cho số liệu thật.

---

## KẾT QUẢ CUỐI CÙNG

**Model được chọn: `microsoft/deberta-v3-small` (B_small_from_scratch)** — 92.75%
Test Accuracy, 92.74% Test F1-macro, 170.79ms latency CPU trung bình (đo trên máy
sạch). Chi tiết đầy đủ + confusion breakdown per-class: xem
[`models/nli_evidence_benchmark_report.md`](models/nli_evidence_benchmark_report.md).

Model đã nằm sẵn ở `models/nli_evidence_v1/` (gitignored, không commit — mỗi máy
cần model file thật thì tự copy hoặc train lại theo hướng dẫn dưới).

**1 bug quan trọng đã phát hiện và sửa giữa chừng**: lần train đầu tiên trên Colab
báo model A/B chậm hơn C tới 17 lần (latency 4-5 GIÂY/câu) — điều tra ra là do
checkpoint gốc của Microsoft (`deberta-v3-xsmall`/`-small`) publish sẵn ở fp16,
notebook không ép `torch_dtype=float32` nên A/B bị train+lưu ở fp16, suy luận fp16
trên CPU (không Tensor Core) chậm hơn fp32 hàng chục lần. Đã convert lại 2
checkpoint (fp16→fp32, không cần train lại, F1-macro không đổi) và sửa notebook
để không lặp lại. Xem chi tiết trong báo cáo benchmark.

---

## 0. Tóm tắt quyết định (đọc mục này nếu vội)

| Câu hỏi | Quyết định | Vì sao |
|---|---|---|
| Máy cá nhân hay Google Colab để **train**? | **Google Colab (T4 GPU, free)** | Máy hiện tại chạy PyTorch bản CPU-only, `torch.cuda.is_available() == False`. Train transformer trên CPU khả thi cho pipeline nhỏ (đã smoke-test) nhưng chậm hơn GPU khoảng 15-30 lần — không hợp lý cho việc so sánh 3 model. |
| Máy cá nhân hay Colab cho **sinh dataset, đánh giá, tích hợp**? | **Máy cá nhân** | Sinh dataset chỉ gọi LLM API (không cần GPU) — đã chạy thật. Đánh giá cuối + đo latency + tích hợp vào `src/services/` cũng chạy CPU, đúng với môi trường EC2 sẽ deploy — đo trên Colab GPU cho số liệu sai lệch (đã xác nhận thật sự xảy ra, xem "KẾT QUẢ CUỐI CÙNG"). |
| Train mấy model? | **3 model, trên cùng 1 dataset, 2 trục so sánh** — đã train xong cả 3 | Trục 1: kích thước (`deberta-v3-xsmall` 90.51% F1 vs `deberta-v3-small` 92.74% F1 — lớn hơn giúp ích rõ). Trục 2: transfer learning từ NLI pretrained (`deberta-v3-xsmall` 90.51% vs `cross-encoder/nli-deberta-v3-xsmall` 90.72% — gần như không khác biệt, nằm trong biên độ nhiễu). |
| EC2 instance tối thiểu? | **t3.small (2GB) khả thi nhưng biên độ hẹp, khuyến nghị t3.medium (4GB)** — model thật nặng hơn ước tính ban đầu (549MB fp32, không phải ~280MB) vì `deberta-v3-small` lớn hơn `-xsmall`. Xem mục 7 (đã cập nhật số liệu thật). |

**Đã chạy xong — mục này giữ lại làm hướng dẫn nếu cần train lại từ đầu sau này**
(ví dụ đổi dataset lớn hơn, thử thêm model khác):

1. [colab.research.google.com](https://colab.research.google.com/) → `File` → `Upload notebook` → `scripts/finetune_nli/02_Train_and_Eval_Colab.ipynb` → `Runtime` → `Change runtime type` → **T4 GPU**.
2. `Runtime` → `Run all`. Ở Cell 2 upload `train.jsonl`/`val.jsonl`/`test.jsonl` (từ `scripts/finetune_nli/data/`, chạy `01_generate_dataset.py` lại nếu muốn dataset mới/lớn hơn).
3. ~10-15 phút cho cả 3 model (đã tối ưu hơn ước tính ban đầu). Cell cuối tự tải `comparison_report.json`.
4. Giải nén model được chọn vào `models/nli_evidence_v1/`, chạy `python scripts/finetune_nli/03_compare_models.py --report comparison_report.json` để sanity-check + xuất báo cáo.

**3 lỗi thật đã gặp và sửa trong lần chạy vừa rồi** (đã sửa sẵn trong notebook,
không cần lo nếu chạy lại từ file hiện tại trong repo):
- `torch --upgrade` làm lệch ABI với `torchvision` có sẵn của Colab → Cell 1 không
  còn upgrade torch nữa.
- `warmup_ratio` bị đổi API ở bản `transformers` mới nhất → đổi sang `warmup_steps`
  tính tay + tự lọc kwargs không được hỗ trợ thay vì crash cứng.
- `fp16=True` + kiến trúc DeBERTa-v3 → `ValueError: Attempting to unscale FP16
  gradients` → tắt hẳn `fp16=False`, thêm `adam_epsilon=1e-6` (khuyến cáo chính
  thức của đội DeBERTa để tránh NaN loss trên fp32).

---

## 1. Trạng thái hiện tại — "đã ổn hết chưa"

Trước khi vào Module 1: nhánh `fix/test` đang sạch, đã đồng bộ với `origin/fix/test`
(2 commit gần nhất — port cải tiến synthesis từ `feat/synthesis-fast-v2-ui` và fix
2 bug thật trong `ragas_eval_service.py` — đã lên cả 2 remote). Không có việc gì
tồn đọng từ phiên làm việc trước.

**1 điểm cần bạn tự kiểm tra (không tự sửa được vì không có quyền)**: `git remote -v`
cho thấy remote `origin` (fetch) đang nhúng thẳng 1 Personal Access Token GitHub
(`ghp_...`) trong URL, lưu plaintext trong `.git/config` trên máy bạn. Không phải lỗi
tôi gây ra và không rò rỉ thêm gì qua việc tôi đọc nó, nhưng nên đổi sang SSH key hoặc
Git Credential Manager thay vì PAT nhúng trong URL — nếu máy này từng bị `git remote -v`
dán ra chỗ công khai (issue, log, chat) thì token đó nên được revoke ngay.

---

## 2. Kiến trúc Động cơ Lượng hóa 3 Tầng (không đổi so với bản gốc)

```
Claim tách ra từ đoạn văn
        │
        ▼
┌───────────────────┐
│ Tầng 1: Exact/     │  So khớp chuỗi nhanh, không cần AI.
│ Fuzzy Matching     │  Claim trùng >90% từ vựng bản gốc -> Supported ngay.
└─────────┬──────────┘
          │ (claim không match rõ ràng)
          ▼
┌───────────────────┐
│ Tầng 2: Custom NLI │  ĐÂY LÀ PHẦN MODULE 1 TRAIN.
│ Cross-Encoder      │  supported / contradicted / insufficient + confidence.
└─────────┬──────────┘
          │ (confidence thấp, 0.4-0.8 — "lửng lơ")
          ▼
┌───────────────────┐
│ Tầng 3: LLM-as-a-  │  Đẩy qua LLM router (ainvoke_with_failover), có giải
│ Judge (dự phòng)   │  thích (explainability). Chỉ gọi khi Tầng 2 không chắc.
└────────────────────┘
```

Toán học lượng hóa (không đổi):
- **Faithfulness ($F$)** = (số claim `Status == supported`) / (tổng số claim) × 100%
- **Citation Precision ($CP$)** = trích dẫn trúng đích / tổng trích dẫn
- **Hallucination Rate ($H$)** = 100% − $F$

`supported` / `contradicted` / `insufficient` không phải nhãn tự đặt mới — đây
chính là `EntailmentStatus` đã tồn tại sẵn trong
[`src/models/synthesis_schemas.py`](src/models/synthesis_schemas.py:25), dùng cho
cơ chế kiểm chứng bằng LLM hiện có
([`src/services/claim_verification_policy.py`](src/services/claim_verification_policy.py)).
Model Tầng 2 dùng đúng 3 nhãn này để cắm thẳng vào pipeline hiện tại mà không cần
lớp dịch nhãn nào — đây là điểm khác biệt quan trọng so với bản kế hoạch gốc (bản
gốc không nói rõ nhãn dùng ở đâu).

---

## 3. Vì sao Google Colab cho việc TRAIN, không phải máy cá nhân

Đo trực tiếp trên máy đang code (2026-08-28):

```
torch version: 2.13.0+cpu
CUDA available: False
CPU: Intel(R) Core(TM) i7-10850H @ 2.70GHz
RAM: 31.64 GB
```

Máy có RAM rất thoải mái (31.64GB — dư sức chứa bất kỳ ứng viên nào trong 3 model),
nhưng **không có GPU** — bản PyTorch cài trên máy còn là build CPU-only. Đã smoke-test
thật (xem mục 8) để đo chênh lệch thay vì đoán:

- Train `deberta-v3-xsmall`, 2 epoch, 345 mẫu, CPU cục bộ: xem số liệu thật ở mục 8.2.
- Trên Colab T4 (ước tính dựa trên throughput T4 công khai cho model cùng lớp
  ~22-140M tham số): nhanh hơn CPU khoảng **15-30 lần** cho cùng workload.

**Kết luận**: sinh dataset (chỉ gọi LLM API, không cần GPU) và bước tích hợp/đánh giá
cuối (phải đo trên CPU vì đó là môi trường deploy thật) chạy ở máy cá nhân. Riêng
bước **train 3 model để so sánh** — vốn cần chạy nhiều epoch × 3 model × có thể cần
thử lại nếu learning rate chưa hợp lý — chuyển hẳn sang Colab T4 (miễn phí) để không
tốn hàng giờ chờ đợi trên máy cá nhân mà kết quả vẫn giống hệt (cùng 1 notebook, cùng
dataset, cùng seed).

---

## 4. Dataset huấn luyện — ĐÃ SINH THẬT, không phải kế hoạch suông

Bản gốc dự định "dùng Gemini sinh 2.000 cặp câu". Bản này đã **chạy thật** với script
[`scripts/finetune_nli/01_generate_dataset.py`](scripts/finetune_nli/01_generate_dataset.py),
lấy premise từ chính kho PDF thật đã nạp vào vector store của dự án (đa lĩnh vực —
Y tế/ECG, Robotics/Vision-Language, Toán tối ưu hoá — giống đúng cách
[`scripts/train_reranker.py`](scripts/train_reranker.py) từng làm khi train reranker
3 domain), KHÔNG dùng dữ liệu tổng hợp tách rời khỏi domain thật của dự án.

**Số liệu thật — bộ dataset dùng để train 3 model cuối cùng (seed=42, `--n-premises 900`):**

| Chỉ số | Giá trị |
|---|---|
| Premise lấy từ vector store | 900 yêu cầu → 308 lấy được (giới hạn bởi tổng số chunk đủ dài/đa dạng nguồn hiện có trong vector store — 980 chunk tổng, 13 paper nguồn) |
| Số paper nguồn khác nhau | 13 |
| Tỉ lệ sinh triplet thành công | 308/308 = **100%** |
| Thời gian sinh (qua OpenAI `gpt-4o-mini`, concurrency=15) | **35.2 giây** |
| Tổng số mẫu (premise, claim, nhãn) | **924** (648 train / 138 val / 138 test) |
| Cân bằng nhãn (train) | supported: 216 · contradicted: 216 · insufficient: 216 (hoàn toàn cân bằng) |

(Bản đầu tiên chạy thử với 163 premise/489 mẫu để xác nhận pipeline hoạt động
đúng — đã tăng lên bộ trên trước khi train chính thức, vì test set 72 mẫu/24
mỗi nhãn cho sai số thống kê quá lớn để tin tưởng kết luận so sánh 3 model.)

**1 bug thật đã sửa trong lúc làm bước này** — không liên quan trực tiếp tới model
nhưng phải sửa để chạy được: task LLM mới (`generate_nli_training_triplet`) mặc định
route qua Gemini, mà Gemini free-tier giới hạn cứng **20 request/ngày/model**
(xem `PROJECT_STANDARDS.md` mục 3 — đúng bug đã từng làm hỏng 2 tab khác trước đây).
Chạy 6 premise đầu tiên để test mất **148.9 giây** (rơi vào cơ chế fail-loud thay vì
lỗi âm thầm, nhưng vẫn chậm vì Gemini). Đã pin task này sang OpenAI trong
[`src/services/llm/router.py`](src/services/llm/router.py) `_TASK_PREFERRED_PROVIDER`
— sau đó 27 premise chạy trong **9.2 giây**, và 163 premise chạy trong **26.1 giây**.

**Muốn dataset lớn hơn cho báo cáo** (ví dụ 1.000-2.000 mẫu như tham vọng ban đầu):
chạy lại với `--n-premises` cao hơn — chi phí gần như tuyến tính (≈0.16 giây/premise
qua OpenAI), không cần tôi can thiệp lại:
```bash
python scripts/finetune_nli/01_generate_dataset.py --n-premises 800 --concurrency 15
```

**Chất lượng nhãn** — đã đọc thủ công một số mẫu (không chỉ tin số liệu), ví dụ:
- `supported`: "High-resolution electrocardiography assumes a fixed beat-to-beat morphology and requires a sampling rate of at least 1 kHz..." — đúng, khớp premise.
- `contradicted`: premise nói "sampling rate is at least 1 kHz", claim bị lật thành "operates effectively with sampling rates below 250 Hz" — sai rõ ràng, không phải diễn đạt lại vô hại.
- `insufficient`: cùng chủ đề nén tín hiệu ECG nhưng đưa ra 1 khẳng định (wavelet transform tốt hơn time-domain) mà đoạn premise không hề nhắc tới — hợp lý, không phải câu lạc đề trắng trợn.

---

## 5. Thiết kế so sánh 3 model — 2 trục, không phải 3 lựa chọn ngẫu nhiên

| # | Model | Nguồn gốc weight | Trục so sánh trả lời được |
|---|---|---|---|
| **A** | `microsoft/deberta-v3-xsmall` | Chỉ pretrain MLM chung, train NLI **từ đầu** trên dataset của ta | Baseline nhỏ nhất |
| **B** | `microsoft/deberta-v3-small` | Chỉ pretrain MLM chung, train NLI **từ đầu** | So A vs B: **kích thước lớn hơn có giúp ích không?** |
| **C** | `cross-encoder/nli-deberta-v3-xsmall` | Đã pretrain sẵn trên SNLI+MultiNLI (transfer learning), fine-tune tiếp trên dataset của ta | So A vs C (cùng kiến trúc): **transfer learning từ NLI có giúp ích không?** |

Đây chính là điểm "làm chủ công nghệ" mà đề bài hackathon gốc nhắm tới — không chỉ
chọn 1 model rồi train, mà chứng minh được **hiểu vì sao** một lựa chọn tốt hơn
(hiệu ứng kích thước tách biệt khỏi hiệu ứng transfer learning).

**Số đo thật về kích thước checkpoint SAU KHI TRAIN** (đo trên đĩa, fp32, sau khi
sửa bug dtype — xem "KẾT QUẢ CUỐI CÙNG" đầu file):

| Model | Checkpoint fp32 sau train |
|---|---|
| `A_xsmall_from_scratch` | 278.2 MB |
| `B_small_from_scratch` | **549.3 MB** |
| `C_xsmall_nli_pretrained` | 278.2 MB |

A và C có cùng kích thước dù khác nguồn gốc (cả hai đều kiến trúc "xsmall" 12 lớp,
hidden_size=384) — B ("small", chỉ 6 lớp nhưng hidden_size=768) lớn gần gấp đôi.
Số đo ban đầu qua HuggingFace Hub API trước khi train (241.5/286.1/283.4 MB) gần
đúng cho A/C nhưng **không dự đoán được** kích thước B thật (checkpoint gốc trên
Hub có thể khác cấu trúc lưu trữ so với sau khi `Trainer.save_model()`) — bài học:
số đo trước khi train chỉ mang tính tham khảo, số quyết định luôn là đo sau khi
có checkpoint thật.

**Nhãn nhất quán**: cả 3 model đều được `AutoModelForSequenceClassification.from_pretrained(
model_name, num_labels=3, id2label=..., label2id=...)` với `LABEL2ID = {"contradicted": 0,
"insufficient": 1, "supported": 2}` — dù model C đã có sẵn đầu phân loại NLI 3 lớp
(entailment/neutral/contradiction theo thứ tự SNLI gốc), việc khởi tạo lại đầu phân
loại theo đúng thứ tự nhãn của dự án là bắt buộc để 3 model có thể so sánh công bằng
trên cùng 1 confusion matrix, và để tích hợp vào `src/services/nli_checker.py` không
cần logic dịch nhãn riêng cho từng model.

**Pipeline train/eval**: [`scripts/finetune_nli/02_Train_and_Eval_Colab.ipynb`](scripts/finetune_nli/02_Train_and_Eval_Colab.ipynb).
- Train/val/test tách bạch thật (không đánh giá trên chính tập train — lỗi phổ biến
  nhất khiến số liệu báo cáo không đáng tin).
- `EarlyStoppingCallback` theo dõi `f1_macro` trên tập val, không phải accuracy đơn
  thuần (accuracy có thể cao giả tạo nếu model chỉ đoán nhãn đa số).
- Đo lại **latency suy luận trên CPU** ngay trong notebook (ép `model.to("cpu")` dù
  train bằng GPU) — vì đó là điều kiện thật khi deploy lên EC2, đo trên GPU sẽ cho số
  liệu sai lệch không dùng được cho quyết định triển khai.
- Quy tắc chọn winner: ưu tiên `test_f1_macro`; nếu 2+ model cách nhau dưới 1.5 điểm %
  (nằm trong biên độ nhiễu của 1 lần train trên dataset nhỏ), chọn theo latency CPU
  thấp nhất.

---

## 6. Metrics cho báo cáo (số liệu thật, không phải mô tả suông)

Mỗi model, đo trên **tập test chưa từng thấy lúc train/chọn checkpoint**:

- Test Accuracy, Test F1-macro, Precision/Recall macro
- Confusion matrix đầy đủ (3×3) + `classification_report` per-class
- Số tham số thật, dung lượng đĩa thật (MB)
- Thời gian train thật (giây, trên T4)
- Latency suy luận CPU: trung bình + p95 (ms/cặp câu) — đo trên 20 mẫu test thật
- (Bước 3, `03_compare_models.py`) Đo lại lần nữa TRÊN MÁY LOCAL bằng đúng phiên bản
  `transformers` cài trong venv của dự án — phòng trường hợp Colab dùng bản mới hơn
  làm model train xong nhưng load lỗi ở production.

Output cuối: [`models/nli_evidence_benchmark_report.md`](models/nli_evidence_benchmark_report.md)
theo đúng format bảng đã dùng trong
[`models/benchmark_report.md`](models/benchmark_report.md) (báo cáo benchmark
reranker có sẵn trong repo) — nhất quán style báo cáo giữa các module.

**Kết quả thật (bảng đầy đủ + confusion breakdown per-class + phân tích trong báo
cáo trên):**

| Model | Test Accuracy | Test F1-macro | Kích thước fp32 | CPU latency avg |
|---|---|---|---|---|
| **B_small_from_scratch 🏆** | **92.75%** | **92.74%** | 549.3 MB | 170.79 ms |
| C_xsmall_nli_pretrained | 90.58% | 90.72% | 278.2 MB | 122.75 ms |
| A_xsmall_from_scratch | 90.58% | 90.51% | 278.2 MB | 128.82 ms |

Model B đánh giá lại trên **toàn bộ** 138 mẫu test (không chỉ tin số tổng hợp):
93.5% đúng trên nhãn `supported`, 87.0% trên `contradicted`, 97.8% trên
`insufficient` — không lệch về 1 nhãn, phân bố dự đoán cân bằng.

---

## 7. Tính khả thi khi deploy lên AWS EC2

### 7.1. RAM — tính lại bằng số đo thật (model B, 549.3MB fp32 — nặng hơn ước tính ban đầu)

Ngân sách RAM ước tính cho **1 process** `uvicorn` đã chạy (baseline: OS + FastAPI +
ChromaDB embedded + model embedding MiniLM đang dùng sẵn ≈ 500-700MB theo quan sát
thực tế khi vá lỗi EC2 phiên trước — chưa đo chính xác bằng `free -h`, xem việc cần
làm bên dưới), CỘNG THÊM model NLI đã chọn (B, `deberta-v3-small`):

| Thành phần | RAM ước tính khi load (fp32, PyTorch) |
|---|---|
| Baseline hệ thống hiện tại (chưa có NLI) | ~500-700 MB *(cần xác nhận — xem lệnh bên dưới)* |
| + model B đã chọn (549.3MB checkpoint fp32) | + ~650-950 MB khi load vào RAM (thường 1.2-1.7× dung lượng file, cộng buffer suy luận) |
| **Tổng cộng ước tính** | **~1.15GB - 1.65GB** |

| Loại EC2 | RAM | Đủ dùng? |
|---|---|---|
| `t2.micro` (free tier, 1GB) | 1GB | ❌ Chắc chắn sập (OOM) |
| `t3.small` (2GB) | 2GB | ⚠️ Khả thi nhưng biên độ hẹp (chỉ còn dư ~350-850MB cho spike/nhiều request đồng thời) — **không còn thoải mái như ước tính ban đầu** vì model B nặng gần gấp đôi các model xsmall |
| `t3.medium` (4GB) | 4GB | ✅ Thoải mái, khuyến nghị nếu có thể nâng cấp |

**Nếu muốn giữ `t3.small`**, có 2 lựa chọn hợp lý hơn quantize (đơn giản, ít rủi ro
dependency hơn nhiều so với đường ONNX):
1. **Đổi sang model A hoặc C thay vì B** — cả hai chỉ 278.2MB (~nửa B), Test F1-macro
   chỉ kém B khoảng 2 điểm % (nằm gần biên độ nhiễu thống kê của test set 138 mẫu —
   xem mục 6), và C còn có latency thấp nhất (122.75ms). Đây là đánh đổi thực dụng
   nếu RAM baseline EC2 đo được sát giới hạn.
2. Quantize model B sang **ONNX INT8** (giảm còn ~25% dung lượng, ~140MB) —
   `optimum[onnxruntime]` **đã biết xung đột dependency với `sentence-transformers==6.0.0`**
   hiện dùng trong dự án (xem lịch sử phiên trước — lý do embedding model đã phải đổi
   từ gte-modernbert sang MiniLM). Không lặp lại việc cài `optimum[onnxruntime]` mà
   không kiểm tra trước; `torch.quantization.quantize_dynamic` (không cần optimum,
   giảm ít hơn ONNX nhưng an toàn dependency) là phương án đầu tiên nên thử.

**Việc cần làm trước khi chốt** (không thể tự làm — không có SSH/AWS CLI truy cập
trong phiên này): SSH vào EC2, chạy `free -h` để biết RAM baseline THẬT hiện tại,
rồi đối chiếu bảng trên để quyết định giữa 3 phương án (nâng `t3.medium` / đổi
sang A hoặc C / quantize B).

### 7.2. CPU — nghẽn cổ chai Event Loop (bản gốc đã nói đúng, giữ nguyên)

Deberta-v3-xsmall/small suy luận CPU đo được (mục 8.2, máy local) — dùng số đo THẬT
thay cho ước lượng "0.1-0.2s/câu" của bản gốc. Do EC2 không có Celery worker
(`PROJECT_STANDARDS.md` mục 6 xác nhận `BackgroundTasks` chạy trong chính tiến trình
`uvicorn`), **bắt buộc** dùng `asyncio.to_thread` khi gọi model — đã implement sẵn
trong [`src/services/nli_checker.py`](src/services/nli_checker.py)`.check_many()`,
theo đúng pattern PROJECT_STANDARDS yêu cầu (không phải việc "nhớ làm sau", đã có
sẵn trong code).

### 7.3. Cách bật khi model đã sẵn sàng

```bash
# .env trên EC2 (KHÔNG tự đồng bộ với .env local — sửa tay theo PROJECT_STANDARDS mục 2.5)
NLI_EVIDENCE_ENABLED=true
NLI_EVIDENCE_MODEL_PATH=./models/nli_evidence_v1
```
`src/config.py` mặc định `NLI_EVIDENCE_ENABLED=false` — an toàn khi deploy code này
lên EC2 trước khi model huấn luyện xong (giống pattern `synthesis_mode="legacy"`,
`fast_v2_reranker="identity"` đã dùng trong dự án: tính năng mới luôn tắt mặc định,
bật rõ ràng bằng tay sau khi đã xác nhận model chạy đúng).

---

## 8. Đã làm — Còn lại (trạng thái thật, không phải lộ trình dự kiến)

### 8.1. Đã làm xong (chạy thật, toàn bộ trong phiên này)

- [x] Đo máy local: CPU-only, i7-10850H, 31.64GB RAM → xác nhận quyết định dùng Colab.
- [x] `scripts/finetune_nli/01_generate_dataset.py` — script sinh dataset qua LLM
      router. Chạy chính thức: **924 mẫu (308 premise), 100% thành công, 35.2 giây**.
- [x] Phát hiện + sửa bug: task LLM mới hit trần Gemini free-tier 20 req/ngày, đã pin
      sang OpenAI trong `router.py`.
- [x] `scripts/finetune_nli/02_Train_and_Eval_Colab.ipynb` — đã **chạy xong trên
      Colab T4**, cả 3 model. 3 lỗi môi trường thật gặp và sửa giữa chừng (torch/
      torchvision ABI mismatch, `warmup_ratio` bị đổi API, `fp16=True` không tương
      thích DeBERTa) — chi tiết ở mục 0.
- [x] **Phát hiện + sửa bug dtype fp16** khiến latency CPU của A/B đo sai gấp 17 lần
      lúc đầu — xem "KẾT QUẢ CUỐI CÙNG" đầu file. Đã convert lại 2 checkpoint (không
      cần train lại) và sửa notebook để không lặp lại lần sau.
- [x] Đánh giá lại model B trên toàn bộ 138 mẫu test (không chỉ tin số tổng hợp) —
      xác nhận không lệch nhãn, per-class 87-98%.
- [x] `scripts/finetune_nli/03_compare_models.py` — đã chạy, xuất
      `models/nli_evidence_benchmark_report.md`, sanity-check load model bằng đúng
      môi trường Python của dự án — thành công (1.56s load, suy luận đúng).
- [x] Copy model B vào `models/nli_evidence_v1/` (gitignored — xem mục dưới).
- [x] `src/services/nli_checker.py` — lớp tích hợp Tầng 2, theo đúng pattern
      `reranker_service.py` (lazy singleton) + bắt buộc `asyncio.to_thread`, fail-loud
      nếu bật `NLI_EVIDENCE_ENABLED` mà chưa có checkpoint, guard kiểm tra thứ tự nhãn.
- [x] `src/config.py` + `.env.example` — thêm `NLI_EVIDENCE_ENABLED` (mặc định tắt),
      `NLI_EVIDENCE_MODEL_PATH`.
- [x] `src/services/llm/capability.py` — đăng ký task `generate_nli_training_triplet`
      đúng theo PROJECT_STANDARDS mục 2.1.
- [x] `.gitignore` — thêm `models/nli_evidence_v1/`, giữ đúng pattern các model khác
      (`lora_agent*/`, `temp_*/`) không commit weight file vào git.

### 8.2. Tích hợp vào pipeline thật — ĐÃ XONG, đã test cục bộ

Quyết định kiến trúc đã chốt: Tầng 2 **lọc trước** (pre-filter), không thay thế Tầng 3
— chỉ những claim Tier 2 tự tin quyết mới bỏ qua LLM, số còn lại đi qua đúng luồng
LLM-as-Judge hiện có, không đổi hành vi.

- [x] `src/services/nli_checker.py::resolve_claims_via_nli()` — nhận đúng format
      `claims_with_evidence` mà `SynthesisService.cross_paper_analysis()` đã dùng cho
      `verify_claim_set_batch` (không cần lớp chuyển đổi riêng). Luật hợp nhất nhiều
      evidence/claim (model NLI chỉ nhận 1 premise:1 hypothesis):
      - Bất kỳ evidence nào NLI báo `contradicted` với confidence ≥ 0.75 → chốt
        `contradicted` ngay (1 mâu thuẫn thật đủ để không cần chờ các evidence khác).
      - Có evidence `supported` ≥ 0.75 **và** không có evidence nào `contradicted` ở
        BẤT KỲ confidence nào (kể cả thấp) → chốt `supported`. Vế contradiction xét
        khắt khe hơn vế support có chủ đích — tín hiệu mâu thuẫn dù yếu vẫn đáng để
        Tier 3/con người xem, Tier 2 không nên tự ý bỏ qua.
      - Còn lại → không quyết, để nguyên cho Tier 3 xử lý y hệt hiện tại.
- [x] `src/services/synthesis_service.py::cross_paper_analysis()` — chèn Tier 2 ngay
      trước bước build batch LLM call; claim Tier 2 đã quyết bị loại khỏi
      `prepared_for_llm` (không tốn LLM call), decision của cả Tier 2 lẫn Tier 3 gộp
      chung vào 1 dict rồi đi qua **đúng nguyên vẹn** cơ chế
      `sanitize_claim_verification` hiện có (không bypass fail-closed guard chống
      evidence_id hallucinate). Khi tắt `NLI_EVIDENCE_ENABLED` (mặc định), nhánh Tier 2
      không chạy — hành vi y hệt trước khi có Module 1.
      Lỗi hệ thống (`NLIModelUnavailableError` — thiếu checkpoint, sai thứ tự nhãn)
      được bắt riêng, log rõ ràng, rồi để toàn bộ claim rơi xuống Tier 3 cho request đó
      thay vì làm gãy cả phiên tổng hợp.
- [x] `tests/test_services/test_nli_checker.py` — 6 test đơn vị cho luật hợp nhất
      (contradicted/supported/escalate/nhiều claim độc lập/không có evidence/tín hiệu
      mâu thuẫn yếu vẫn chặn support) — dùng `FakeNLIChecker` (double), không load model
      thật, theo đúng pattern test đã có trong repo.
- [x] **Smoke-test thật với model B** (không mock) — 3 tình huống, cả 3 đúng:
      claim đúng khớp 1/2 evidence → `supported`, chỉ chọn evidence liên quan; claim
      lật ngược 1 bất đẳng thức thật → `contradicted`; claim hoàn toàn không liên quan
      tới evidence được cung cấp → không quyết, escalate lên Tier 3 (đúng kỳ vọng).
- [x] Toàn bộ `pytest tests/ -q` (trừ `test_fast_v2/`) — **265 passed**, đúng 3 lỗi
      baseline đã biết trước Module 1 (không phải regression) + 3 lỗi môi trường
      Windows cục bộ đã biết (`test_document_processor.py`, PermissionError không
      liên quan code).

### 8.3. Còn lại — deploy EC2 (theo yêu cầu: để SAU khi test local xong, SAU khi merge main)

1. **SSH vào EC2, chạy `free -h`** để biết RAM baseline thật, đối chiếu mục 7.1 —
   quyết định giữ `t3.small`+đổi model nhỏ hơn, hay nâng `t3.medium`, hay quantize.
2. Copy model đã chọn lên EC2 (`scp -r models/nli_evidence_v1 ubuntu@<EC2_IP>:~/P-165/models/`),
   bật `NLI_EVIDENCE_ENABLED=true` trong `.env` trên EC2, restart `uvicorn`.
3. (Tuỳ chọn) Mở rộng dataset lên >924 mẫu nếu báo cáo cần số liệu chắc chắn hơn nữa.

---

## 9. Rủi ro đã biết

- **Dataset 924 mẫu (648 train) vẫn là quy mô vừa phải, không phải tập lớn** — test
  set 138 mẫu (46/nhãn) cho sai số ước lượng ~±5%, nên chênh lệch F1-macro ~2 điểm %
  giữa 3 model (mục 6) nằm gần biên độ nhiễu này. B là lựa chọn hợp lý nhất với bằng
  chứng hiện có, không phải kết luận thống kê tuyệt đối chắc chắn. Mở rộng dataset là
  việc rẻ (~0.11s/mẫu qua OpenAI) nếu báo cáo cần số liệu chắc chắn hơn.
- **Model B có xu hướng dự đoán sai với câu ngoài phân phối train** (out-of-distribution)
  — phát hiện qua sanity-check thủ công (mục "KẾT QUẢ CUỐI CÙNG"), không phải trên tập
  test chính thức. Hạn chế thật của dataset train quy mô vừa, nên ghi nhận trung thực
  trong báo cáo thay vì chỉ báo cáo con số F1-macro đẹp.
- **`optimum[onnxruntime]` xung đột dependency đã biết** (mục 7.1) — không thử lại
  mà không đọc kỹ lịch sử phiên trước; `torch.quantization.quantize_dynamic` là
  phương án an toàn hơn nếu cần giảm RAM.
- **RAM baseline EC2 hiện tại chưa được đo thật** — mọi số liệu ở mục 7.1 là ước tính
  có căn cứ, không phải số đo trực tiếp. Phải chạy `free -h` trước khi chốt loại
  instance — quan trọng hơn trước vì model B (549.3MB) nặng hơn ước tính ban đầu khá
  nhiều.
- **Model C (`cross-encoder/nli-deberta-v3-xsmall`) có sẵn đầu phân loại NLI 3 lớp
  nhưng thứ tự nhãn gốc (entailment/neutral/contradiction) khác thứ tự dự án dùng**
  — code train đã tự xử lý (khởi tạo lại đầu phân loại theo đúng `LABEL2ID` của dự
  án), nhưng nếu sau này có ai load thẳng checkpoint gốc từ HuggingFace Hub mà không
  qua pipeline train của ta, nhãn output sẽ SAI thứ tự — `nli_checker.py` đã có guard
  kiểm tra `id2label` khớp đúng `{0: contradicted, 1: insufficient, 2: supported}`
  trước khi dùng, từ chối load nếu không khớp.
- **Không train lại checkpoint đã convert dtype (A, B) từ đầu** — chỉ convert fp16→fp32
  của trọng số đã học, không train lại. Nếu cần tái tạo hoàn toàn từ đầu (ví dụ đổi
  dataset), notebook đã sửa `torch_dtype=torch.float32` nên lần train tiếp theo sẽ
  không dính lại bug này, không cần bước convert thủ công nữa.
