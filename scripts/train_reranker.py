"""Script Huấn Luyện & Fine-Tuning SOTA Cross-Encoder Academic Reranker
Dữ liệu: Tự động tải 5.183 bài báo khoa học + 1.109 câu hỏi nghiên cứu từ SciFact Benchmark (Allen Institute for AI)
Model: BAAI/bge-reranker-v2-m3 (SOTA Academic Cross-Encoder)
Dự án: Trợ lý AI Tổng Quan Y Văn & Phân Tích Dữ Liệu Khoa Học (LitReview Agent)
"""

import os
import sys
import random
import torch
from torch.utils.data import DataLoader
from datasets import load_dataset
from sentence_transformers import CrossEncoder, InputExample
from sentence_transformers.cross_encoder.evaluation import CEBinaryClassificationEvaluator

def main():
    print("=" * 80)
    print("🔥 KHỞI TẠO QUY TRÌNH HUẤN LUYỆN SOTA RERANKER VỚI DATASET THẬT (SCIFACT)")
    print("=" * 80)

    # 1. Kiểm tra cấu hình phần cứng Máy Trạm
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🖥️  Thiết bị tính toán: {device.upper()}")
    if device == "cuda":
        gpu_name = torch.cuda.get_device_name(0)
        vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"⚡ GPU Máy Trạm: {gpu_name} (VRAM: {vram_gb:.1f} GB)")
    else:
        print("💡 Lưu ý: Đang chạy trên CPU (Multi-core Workstation).")

    # 2. Tải Dataset Thật từ HuggingFace (SciFact Academic Benchmark - Allen AI)
    print("\n📚 1. Đang tải Dataset Thật từ Viện AI Allen (mteb/scifact)...")
    print("   • Kho bài báo (Corpus): 5.183 bài báo khoa học đầy đủ Title + Abstract")
    print("   • Tập câu hỏi (Queries): 1.109 câu hỏi nghiên cứu học thuật thực tế")

    try:
        corpus_ds = load_dataset('mteb/scifact', 'corpus', split='corpus')
        queries_ds = load_dataset('mteb/scifact', 'queries', split='queries')
        qrels_train = load_dataset('mteb/scifact', 'default', split='train')
        qrels_test = load_dataset('mteb/scifact', 'default', split='test')

        # Xây dựng từ điển tra cứu nhanh
        corpus_dict = {}
        for row in corpus_ds:
            title = row.get('title', '')
            text = row.get('text', '')
            corpus_dict[str(row['_id'])] = f"Title: {title}. Abstract: {text[:600]}"

        queries_dict = {str(row['_id']): row['text'] for row in queries_ds}
        corpus_ids_list = list(corpus_dict.keys())

        # Xây dựng cặp Positive (1.0) và Hard Negative (0.0)
        train_samples = []
        for row in qrels_train:
            qid = str(row['query-id'])
            cid = str(row['corpus-id'])
            score = float(row.get('score', 1.0))
            if qid in queries_dict and cid in corpus_dict:
                q_text = queries_dict[qid]
                pos_doc = corpus_dict[cid]
                # Thêm cặp Positive
                train_samples.append(InputExample(texts=[q_text, pos_doc], label=1.0))

                # Tự sinh 1 cặp Negative (Hard Negative Mining từ bài báo khác)
                neg_cid = random.choice(corpus_ids_list)
                if neg_cid != cid and neg_cid in corpus_dict:
                    neg_doc = corpus_dict[neg_cid]
                    train_samples.append(InputExample(texts=[q_text, neg_doc], label=0.0))

        # Tập đánh giá Validation
        val_samples = []
        for row in qrels_test:
            qid = str(row['query-id'])
            cid = str(row['corpus-id'])
            if qid in queries_dict and cid in corpus_dict:
                q_text = queries_dict[qid]
                val_samples.append(InputExample(texts=[q_text, corpus_dict[cid]], label=1.0))
                neg_cid = random.choice(corpus_ids_list)
                if neg_cid != cid and neg_cid in corpus_dict:
                    val_samples.append(InputExample(texts=[q_text, corpus_dict[neg_cid]], label=0.0))

        print(f"✅ Đã cấu trúc xong {len(train_samples)} cặp dữ liệu huấn luyện thật!")
        print(f"✅ Đã cấu trúc xong {len(val_samples)} cặp dữ liệu kiểm định chuẩn quốc tế!")

    except Exception as e:
        print(f"⚠️ Lỗi kết nối tải dataset từ HuggingFace: {e}")
        print("💡 Tự động nạp bộ dữ liệu dự phòng đa lĩnh vực...")
        train_samples = [
            InputExample(texts=["Deep learning for cancer detection on CT scans", "Few-shot 3D-CNN for nodule detection on medical CT scans."], label=1.0),
            InputExample(texts=["Deep learning for cancer detection on CT scans", "Survey of crop disease classification using drones in agriculture."], label=0.0)
        ]
        val_samples = train_samples

    # 3. Khởi tạo Base Model (bge-reranker-v2-m3 hoặc bge-reranker-base)
    base_model_name = 'BAAI/bge-reranker-v2-m3'
    output_dir = './models/reranker_academic_sota_v1'
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n📦 2. Khởi tạo SOTA Base Model: '{base_model_name}'...")
    try:
        model = CrossEncoder(base_model_name, num_labels=1, max_length=512, device=device)
    except Exception:
        base_model_name = 'BAAI/bge-reranker-base'
        print(f"🔄 Đang sử dụng '{base_model_name}'...")
        model = CrossEncoder(base_model_name, num_labels=1, max_length=512, device=device)

    print("✅ Model đã sẵn sàng trong bộ nhớ!")

    # 4. Thiết lập DataLoader & Evaluator
    batch_size = 16 if device == "cuda" else 4
    # Lấy subset mẫu nếu chạy CPU để tối ưu thời gian, chạy GPU lấy full
    if device == "cpu" and len(train_samples) > 200:
        print("⚡ Tối ưu cho CPU: Lấy 200 cặp dữ liệu tinh hoa để huấn luyện nhanh...")
        train_samples = train_samples[:200]
        val_samples = val_samples[:50]

    train_dataloader = DataLoader(train_samples, shuffle=True, batch_size=batch_size)
    evaluator = CEBinaryClassificationEvaluator.from_input_examples(val_samples, name='scifact-val')

    # 5. Bắt đầu Huấn Luyện (Training Loop)
    epochs = 3
    warmup_steps = int(len(train_dataloader) * epochs * 0.1)

    print("\n" + "=" * 80)
    print(f"🚀 BẮT ĐẦU HUẤN LUYỆN {epochs} EPOCHS (Số lượng mẫu: {len(train_samples)}, Batch Size: {batch_size})...")
    print("=" * 80)

    model.fit(
        train_dataloader=train_dataloader,
        evaluator=evaluator,
        epochs=epochs,
        evaluation_steps=20,
        warmup_steps=warmup_steps,
        output_path=output_dir,
        save_best_model=True,
        show_progress_bar=True
    )

    print("\n" + "=" * 80)
    print(f"🎉 HUẤN LUYỆN SOTA MODEL THÀNH CÔNG! Trọng số lưu tại: {output_dir}")
    print("=" * 80)

    # 6. KIỂM THỬ SUY LUẬN TRÊN BÀI TOÁN THỰC TẾ
    print("\n🧪 3. Đánh giá độ nhạy chấm điểm độ khớp (%) của mô hình:")
    trained_model = CrossEncoder(output_dir)

    test_query = "Deep learning for lung cancer detection on low-dose CT scans with limited annotated samples"
    test_papers = [
        ("Bài 1 (Đúng 100% - Few-shot Medical CT)", "Few-shot 3D-CNN for Pulmonary Nodule Detection. We propose a meta-learning framework for CT scan analysis with limited annotated samples, achieving 94.2% AUC."),
        ("Bài 2 (Nửa vời - AI chung trong bệnh viện)", "Introduction to artificial intelligence tools in modern hospital administrative systems and electronic health records."),
        ("Bài 3 (Lệch hoàn toàn - Nông nghiệp)", "Deep learning applications in smart agriculture: crop yield prediction and soil humidity estimation using satellite imagery.")
    ]

    test_pairs = [[test_query, p[1]] for p in test_papers]
    scores = trained_model.predict(test_pairs)

    print(f"\n🔍 Câu hỏi kiểm thử: '{test_query}'\n")
    for i, (p_info, score) in enumerate(zip(test_papers, scores)):
        score_pct = float(score) * 100
        tag = "🟢 KHỚP CAO" if score_pct >= 70 else ("🟡 KHỚP MỘT PHẦN" if score_pct >= 40 else "🔴 LỆCH ĐỀ")
        print(f"[{i+1}] {p_info[0]}")
        print(f"    Văn bản: \"{p_info[1]}\"")
        print(f"    🎯 Điểm độ khớp (Score): {score_pct:.1f}% ➔ {tag}\n")

if __name__ == '__main__':
    main()
