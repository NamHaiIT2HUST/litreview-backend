"""
KỊCH BẢN THỰC NGHIỆM ĐỐI SÁNH (BENCHMARK) 3 MÔ HÌNH RERANKER HẠNG NẶNG
Lĩnh vực: Toán học, Y tế, Robotics

Máy trạm mục tiêu: DELL PRECISION 7550 (Sử dụng GPU)
Quy trình: Train 80% -> Test 20% -> Báo cáo kết quả -> Lưu Model Tốt Nhất
"""

import os
import random
import time
import json
import torch
from torch.utils.data import DataLoader
from sentence_transformers import CrossEncoder, InputExample
from sentence_transformers.cross_encoder.evaluation import CEBinaryClassificationEvaluator

# ==============================================================================
# 1. DANH SÁCH ỨNG VIÊN (ĐÃ ĐIỀU CHỈNH CHO LAPTOP ĐỂ CHẠY NHANH HƠN)
# ==============================================================================
CANDIDATE_MODELS = [
    {
        "id": "bge-base",
        "name": "BAAI/bge-reranker-base",
        "description": "Cân bằng hoàn hảo: 278M params, cực kỳ thông minh nhưng nhẹ bằng một nửa bản Large. Chạy tầm 1.5 - 2 tiếng."
    },
    {
        "id": "minilm-l6",
        "name": "cross-encoder/ms-marco-MiniLM-L-6-v2",
        "description": "Siêu nhẹ (22M params). Train cực nhanh chỉ khoảng 15-20 phút, rất tốt để test luồng chạy."
    }
]

# ==============================================================================
# 2. DỮ LIỆU CHUYÊN BIỆT (3 DOMAINS)
# ==============================================================================
DOMAIN_TRAINING_DATA = [
    # Y TẾ (Medical)
    {
        "query": "Deep learning for lung nodule detection on low-dose CT scans",
        "pos": "Few-shot 3D-CNN for Pulmonary Nodule Detection. Meta-learning framework for CT scan analysis with limited annotated medical samples, achieving 94.2% AUC.",
        "neg": "Deep learning in agriculture: crop yield prediction and soil humidity estimation using drone imagery."
    },
    {
        "query": "ECG arrhythmia classification using 1D convolutional neural networks",
        "pos": "Interpretable 1D CNN-Transformer architecture for real-time 12-lead ECG heartbeat classification. Reaches 98.7% sensitivity.",
        "neg": "Blockchain-based decentralized financial consensus mechanisms for cryptocurrency trading."
    },
    {
        "query": "Brain tumor MRI segmentation with uncertainty estimation",
        "pos": "Uncertainty-aware Bayesian Deep Learning for 3D Brain Tumor Segmentation on Multimodal MRI. Improves boundary delineation on BraTS benchmark.",
        "neg": "Social media sentiment analysis during marketing campaigns using NLP."
    },
    # ROBOTICS
    {
        "query": "Deep reinforcement learning for mobile robot autonomous navigation in dynamic environments",
        "pos": "Asynchronous Actor-Critic DRL for Mobile Robot Obstacle Avoidance in Crowded Environments. Validated in Gazebo and Isaac Sim.",
        "neg": "Analysis of customer churn in retail telecommunication networks using random forest."
    },
    {
        "query": "Visual-LiDAR fusion SLAM for autonomous driving in GPS-denied environments",
        "pos": "Tight-coupled LiDAR-Inertial-Visual Odometry and Mapping in Degraded Underground Environments. Multi-sensor fusion graph optimization.",
        "neg": "Methods for organic fertilizer synthesis from municipal solid waste."
    },
    {
        "query": "Sim-to-real transfer for quadruped robot locomotion across rough terrains",
        "pos": "Adversarial domain randomization for robust quadrupedal robot locomotion over slippery terrains. Trained in MuJoCo, deployed to Unitree Go1.",
        "neg": "Historical analysis of urban architectural zoning policies in 19th-century."
    },
    # TOÁN HỌC (Math & Optimization)
    {
        "query": "Non-convex optimization convergence analysis for stochastic gradient descent",
        "pos": "Global Convergence Guarantees for Stochastic Gradient Descent in Non-Convex Deep Networks under the Polyak-Lojasiewicz condition.",
        "neg": "Survey of contemporary high school pedagogical methods for teaching world geography."
    },
    {
        "query": "Proximal gradient methods and ADMM for sparse matrix recovery",
        "pos": "Accelerated Inexact Proximal Alternating Direction Method of Multipliers (ADMM) for Low-Rank and Sparse Matrix Decomposition.",
        "neg": "Impact of remote working policies on employee coffee consumption habits."
    },
    {
        "query": "Physics-informed neural networks PINNs for non-linear partial differential equations",
        "pos": "Adaptive residual sampling in Physics-Informed Neural Networks (PINNs) for solving Navier-Stokes and Burgers PDEs.",
        "neg": "Brand equity measurement of luxury fashion items among Generation Z consumers."
    }
]

def load_and_split_data():
    """Tạo tập Train 80% và Test 20% kết hợp Hard Negatives."""
    print("⏳ Đang chuẩn bị tập dữ liệu (Kết hợp 3 Domains + SciFact Benchmark)...")
    dataset_samples = []

    # 1. Thêm dữ liệu tự định nghĩa (Seed data)
    for item in DOMAIN_TRAINING_DATA:
        dataset_samples.append(InputExample(texts=[item["query"], item["pos"]], label=1.0))
        dataset_samples.append(InputExample(texts=[item["query"], item["neg"]], label=0.0))

    # 2. Tải Full Dataset Học thuật (Hàng ngàn bài báo Y sinh, Khoa học Máy tính)
    try:
        from datasets import load_dataset
        print("   -> Đang tải FULL mteb/scifact (Kho Y sinh & Máy tính)...")
        # Không dùng [:1000] nữa, tải toàn bộ!
        corpus_ds = load_dataset('mteb/scifact', 'corpus', split='corpus', trust_remote_code=True)
        queries_ds = load_dataset('mteb/scifact', 'queries', split='queries', trust_remote_code=True)
        qrels_train = load_dataset('mteb/scifact', 'default', split='train', trust_remote_code=True)
        qrels_test = load_dataset('mteb/scifact', 'default', split='test', trust_remote_code=True)

        corpus_dict = {str(r['_id']): f"{r.get('title','')} - {r.get('text','')}[:800]" for r in corpus_ds}
        queries_dict = {str(r['_id']): r['text'] for r in queries_ds}
        corpus_ids = list(corpus_dict.keys())

        # Gộp Train & Test của SciFact vào làm nguồn data (vì lát nữa ta sẽ tự chia 80/20 lại)
        all_qrels = list(qrels_train) + list(qrels_test)

        for row in all_qrels:
            qid, cid = str(row['query-id']), str(row['corpus-id'])
            if qid in queries_dict and cid in corpus_dict:
                dataset_samples.append(InputExample(texts=[queries_dict[qid], corpus_dict[cid]], label=1.0))
                
                # Tạo 2 Hard Negatives cho mỗi bài báo đúng (Tăng tỷ lệ dữ liệu rác để model học gắt hơn)
                for _ in range(2):
                    neg_id = random.choice(corpus_ids)
                    if neg_id != cid and neg_id in corpus_dict:
                        dataset_samples.append(InputExample(texts=[queries_dict[qid], corpus_dict[neg_id]], label=0.0))
        
        print(f"   -> Đã trộn thành công! Kích thước Dataset hiện tại: {len(dataset_samples)} cặp dữ liệu.")
    except Exception as e:
        print(f"   -> ⚠️ Lỗi khi tải SciFact: {e}")

    # Xáo trộn và chia 80/20
    random.seed(42)
    random.shuffle(dataset_samples)
    split_point = int(len(dataset_samples) * 0.8)
    
    train_set = dataset_samples[:split_point]
    test_set = dataset_samples[split_point:]
    
    print(f"✅ Đã chia dữ liệu: {len(train_set)} cặp Train (80%) | {len(test_set)} cặp Test (20%).\n")
    return train_set, test_set

# ==============================================================================
# 3. HÀM BENCHMARK CHÍNH
# ==============================================================================
def main():
    print("=" * 80)
    print("🏆 BẮT ĐẦU BENCHMARK 3 MÔ HÌNH RERANKER HẠNG NẶNG (DELL PRECISION 7550)")
    print("=" * 80)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🖥️ Thiết bị huấn luyện: {device.upper()}")
    if device == "cuda":
        print(f"⚡ GPU: {torch.cuda.get_device_name(0)}")
        print(f"💾 VRAM khả dụng: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f} GB")

    train_set, test_set = load_and_split_data()
    
    # Tối ưu cực độ cho VRAM 6GB (Quadro RTX 3000)
    batch_size = 2 # Giữ batch_size siêu nhỏ để đảm bảo 100% nằm gọn trong 6GB VRAM
    epochs = 2
    
    train_dataloader = DataLoader(train_set, shuffle=True, batch_size=batch_size)
    # Evaluator xuất F1, AP (Average Precision), Accuracy
    evaluator = CEBinaryClassificationEvaluator.from_input_examples(test_set, name='test_set')
    
    benchmark_results = {}

    for candidate in CANDIDATE_MODELS:
        model_id = candidate["id"]
        model_name = candidate["name"]
        output_path = f"./models/temp_{model_id}"
        
        print("\n" + "=" * 60)
        print(f"🚀 ĐANG HUẤN LUYỆN ỨNG VIÊN: {model_id.upper()}")
        print(f"📦 Tên model gốc: {model_name}")
        print(f"📝 Ghi chú: {candidate['description']}")
        print("=" * 60)

        try:
            # 1. Khởi tạo (Giảm max_length xuống 384 thay vì 512 để tiết kiệm 40% VRAM)
            model = CrossEncoder(model_name, num_labels=1, max_length=384, device=device)
            
            # 2. Huấn luyện (Train) - BẬT MIXED PRECISION (use_amp=True) để cắt đôi VRAM
            start_time = time.time()
            model.fit(
                train_dataloader=train_dataloader,
                epochs=epochs,
                warmup_steps=int(len(train_dataloader) * epochs * 0.1),
                output_path=output_path,
                use_amp=True,  # Kích hoạt FP16 (Siêu tối ưu cho RTX)
                show_progress_bar=True
            )
            train_time = time.time() - start_time
            
            # ÉP LƯU MODEL NGAY LẬP TỨC (Chống mất dữ liệu nếu bị ngắt ngang)
            print("💾 Đang ghi model ra ổ cứng để bảo toàn...")
            model.save(output_path)

            # Đánh giá trên tập Test (20%)
            print(f"🧪 Đang làm bài thi trên Test Set (20%)...")
            eval_metrics = evaluator(model, output_path=output_path)
            
            # Xử lý tương thích phiên bản (SentenceTransformers trả về dict hoặc float)
            if isinstance(eval_metrics, dict):
                # Lấy giá trị Average Precision (AP) từ dict
                eval_score = eval_metrics.get(f"{evaluator.name}_ap", eval_metrics.get("ap", list(eval_metrics.values())[0] if eval_metrics else 0.0))
                if isinstance(eval_score, dict): # Safe fallback
                    eval_score = list(eval_score.values())[0]
            else:
                eval_score = eval_metrics
            
            # Đo tốc độ suy luận (Inference Speed)
            test_pairs = [[ex.texts[0], ex.texts[1]] for ex in test_set[:20]]
            start_inf = time.time()
            model.predict(test_pairs)
            inf_time_per_pair = ((time.time() - start_inf) / 20) * 1000 # tính bằng ms

            benchmark_results[model_id] = {
                "name": model_name,
                "average_precision_score": round(float(eval_score), 4),
                "train_time_sec": round(train_time, 1),
                "inference_ms_per_pair": round(inf_time_per_pair, 2)
            }
            
            print(f"✅ Hoàn thành {model_id} | Điểm AP: {eval_score:.4f} | Tốc độ suy luận: {inf_time_per_pair:.2f} ms/cặp")
            
            # Dọn RAM/VRAM để chạy model tiếp theo
            del model
            torch.cuda.empty_cache()

        except Exception as e:
            print(f"❌ Lỗi khi chạy ứng viên {model_id}: {e}")
            benchmark_results[model_id] = {"error": str(e)}

    # ==============================================================================
    # 4. TỔNG HỢP VÀ GHI BÁO CÁO
    # ==============================================================================
    print("\n" + "=" * 80)
    print("📊 BẢNG KẾT QUẢ BENCHMARK CHUNG CUỘC")
    print("=" * 80)
    
    report_lines = []
    report_lines.append("# Báo cáo Benchmark 3 Mô hình Reranker Hạng Nặng (Toán, Y tế, Robotics)")
    report_lines.append("| Tên Ứng Viên | Tên Model Gốc | Điểm Chính Xác (AP) | Thời gian Train (s) | Tốc độ Rerank (ms/cặp) |")
    report_lines.append("|---|---|---|---|---|")

    best_model_id = None
    best_score = -1

    for model_id, stats in benchmark_results.items():
        if "error" in stats:
            print(f"⚠️ {model_id}: FAILED ({stats['error']})")
            report_lines.append(f"| {model_id} | ERROR | - | - | - |")
        else:
            ap_score = stats['average_precision_score']
            print(f"🏆 {model_id.upper()} | Tên: {stats['name']}")
            print(f"   - Độ chính xác (Average Precision): {ap_score * 100:.2f}%")
            print(f"   - Tốc độ Rerank: {stats['inference_ms_per_pair']} ms/cặp")
            
            report_lines.append(f"| {model_id.upper()} | `{stats['name']}` | **{ap_score * 100:.2f}%** | {stats['train_time_sec']}s | {stats['inference_ms_per_pair']}ms |")

            if ap_score > best_score:
                best_score = ap_score
                best_model_id = model_id

    # Lưu file báo cáo
    os.makedirs("./models", exist_ok=True)
    with open("./models/benchmark_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    print("\n" + "=" * 80)
    if best_model_id:
        print(f"🌟 MÔ HÌNH XUẤT SẮC NHẤT THUỘC VỀ: {best_model_id.upper()} (Điểm AP: {best_score * 100:.2f}%)")
        print("📁 Toàn bộ trọng số đã được lưu tại ./models/temp_" + best_model_id)
        print("📄 Báo cáo chi tiết đã xuất ra: ./models/benchmark_report.md")
    print("=" * 80)
    print("\n📩 HÃY GỬI KẾT QUẢ IN RA MÀN HÌNH (hoặc file benchmark_report.md) CHO AI ĐỂ ĐÁNH GIÁ!")

if __name__ == '__main__':
    main()
