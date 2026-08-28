"""
MODULE 1 — Evidence Quantification Engine
Bước 3: Sau khi Colab train xong cả 3 model (02_Train_and_Eval_Colab.ipynb) và
bạn đã tải `comparison_report.json` + giải nén model thắng cuộc vào
`models/nli_evidence_v1/`, chạy script này để:
  1. In lại bảng so sánh 3 model dưới dạng Markdown (đúng style
     models/benchmark_report.md đã có sẵn trong repo).
  2. Nạp thử model thắng cuộc BẰNG MÔI TRƯỜNG PYTHON THẬT CỦA DỰ ÁN (không
     phải môi trường Colab) để xác nhận nó chạy được trước khi tích hợp vào
     src/services/ -- một model train xong trên Colab (thường mới hơn, khác
     phiên bản `transformers`) đôi khi load lỗi trên môi trường production cũ hơn.
  3. Đo lại latency CPU + RAM peak ngay trên máy sẽ deploy (hoặc máy giống
     EC2 nhất có thể) để số liệu báo cáo phản ánh đúng môi trường thật.

Usage:
    python scripts/finetune_nli/03_compare_models.py --report comparison_report.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import tracemalloc
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

MODELS_DIR = PROJECT_ROOT / "models" / "nli_evidence_v1"
REPORT_OUT = PROJECT_ROOT / "models" / "nli_evidence_benchmark_report.md"


def render_markdown(data: dict) -> str:
    results = data["results"]
    winner = data["winner"]

    lines = [
        "# Báo cáo Benchmark 3 Mô hình NLI — Module 1 Evidence Quantification Engine",
        "",
        "So sánh 3 ứng viên cho tầng Custom Cross-Encoder NLI, cùng huấn luyện/đánh giá",
        "trên 1 dataset 3 nhãn (`supported`/`contradicted`/`insufficient`) sinh từ chính",
        "kho PDF thật của dự án. Xem `scripts/finetune_nli/` cho pipeline đầy đủ.",
        "",
        "| Model | Base checkpoint | Tham số | Kích thước (MB) | Train time (s) | "
        "Test Accuracy | Test F1-macro | CPU latency avg (ms) | CPU latency p95 (ms) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in sorted(results, key=lambda x: -x["test_f1_macro"]):
        star = " 🏆" if r["run_name"] == winner else ""
        lines.append(
            f"| {r['run_name']}{star} | `{r['model_name']}` | {r['n_params']/1e6:.1f}M | "
            f"{r['model_size_mb']:.1f} | {r['train_seconds']:.1f} | "
            f"**{r['test_accuracy']*100:.2f}%** | **{r['test_f1_macro']*100:.2f}%** | "
            f"{r['cpu_latency_ms_avg']:.2f} | {r['cpu_latency_ms_p95']:.2f} |"
        )

    lines += ["", "## Confusion matrix (test set) từng model", ""]
    for r in results:
        lines.append(f"### {r['run_name']}")
        lines.append("")
        lines.append("```")
        lines.append(r["classification_report"])
        lines.append("```")
        lines.append("")

    lines += [
        "## Quy tắc chọn model",
        "",
        "Ưu tiên **Test F1-macro** (chất lượng phân loại quan trọng nhất cho việc phát "
        "hiện hallucination — một hệ thống chấm điểm bằng accuracy đơn thuần có thể đạt "
        "điểm cao chỉ bằng cách luôn đoán nhãn đa số). Khi 2+ model có F1-macro cách nhau "
        "trong 1.5 điểm % (nằm trong biên độ nhiễu ngẫu nhiên của 1 lần train trên dataset "
        "nhỏ), chọn theo CPU latency thấp nhất — vì model chạy inference trên EC2 CPU, "
        "không có GPU.",
        "",
        f"**Model được chọn: `{winner}`**",
    ]
    return "\n".join(lines)


def sanity_check_local_load():
    if not MODELS_DIR.exists():
        print(f"[SKIP] {MODELS_DIR} chưa tồn tại -- giải nén model thắng cuộc vào đây trước.")
        return

    print(f"\nNạp thử model tại {MODELS_DIR} bằng transformers hiện có trong venv của dự án...")
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(str(MODELS_DIR))
    model = AutoModelForSequenceClassification.from_pretrained(str(MODELS_DIR)).to("cpu").eval()
    load_seconds = time.time() - t0

    id2label = model.config.id2label
    print(f"  Load OK trong {load_seconds:.2f}s. Nhãn: {id2label}")

    test_pairs = [
        ("The CQ algorithm converges weakly under a step-size bound of 0 < gamma < 2/||A||^2.",
         "The relaxation parameter must be strictly less than twice the reciprocal of the squared operator norm."),
        ("The CQ algorithm converges weakly under a step-size bound of 0 < gamma < 2/||A||^2.",
         "The step size may be chosen arbitrarily large without affecting convergence."),
        ("The CQ algorithm converges weakly under a step-size bound of 0 < gamma < 2/||A||^2.",
         "The original CQ algorithm was proposed for image reconstruction in radiotherapy."),
    ]

    tracemalloc.start()
    latencies = []
    with torch.no_grad():
        for premise, hyp in test_pairs:
            enc = tokenizer(premise, hyp, truncation=True, max_length=384, return_tensors="pt")
            t0 = time.perf_counter()
            logits = model(**enc).logits
            latencies.append((time.perf_counter() - t0) * 1000)
            pred_id = int(logits.argmax(dim=-1)[0])
            print(f"    -> \"{hyp[:70]}...\" => {id2label[pred_id]} ({latencies[-1]:.1f} ms)")
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"\n  Latency trung bình (3 mẫu, máy hiện tại): {sum(latencies)/len(latencies):.2f} ms")
    print(f"  Peak Python-tracked memory trong lúc inference: {peak/1e6:.1f} MB "
          f"(chưa tính RAM base của process — chỉ phần cấp phát mới trong lúc chạy)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=str, default="comparison_report.json",
                         help="Đường dẫn tới comparison_report.json tải về từ Colab.")
    args = parser.parse_args()

    report_path = Path(args.report)
    if not report_path.exists():
        print(f"Không tìm thấy {report_path}. Tải file này từ Colab (Cell 6) trước.")
        sys.exit(1)

    data = json.loads(report_path.read_text(encoding="utf-8"))
    md = render_markdown(data)

    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.write_text(md, encoding="utf-8")
    print(md)
    print(f"\n\nĐã ghi báo cáo: {REPORT_OUT}")

    sanity_check_local_load()


if __name__ == "__main__":
    main()
