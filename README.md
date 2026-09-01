<div align="center">

<img src="https://raw.githubusercontent.com/AI20K-Build-Phase-Cohort-3/P-165/main/frontend/public/favicon.ico" alt="LitReview Logo" width="64" height="64" />

# LitReview Agent

**LitReview Agent — AI-Powered Systematic Literature Review**

[![Live Demo](https://img.shields.io/badge/Live_Demo-c3--app--165.io.vn-22c55e?style=for-the-badge&logo=googlechrome&logoColor=white)](https://www.c3-app-165.io.vn/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Python](https://img.shields.io/badge/Python_3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org/)

Tự động hóa toàn bộ quy trình **Systematic Literature Review (SLR)** — từ tìm kiếm, sàng lọc AI, đến tổng hợp luận văn với trích dẫn grounded 100% trên DOI thật.

[🌐 Live Demo](https://www.c3-app-165.io.vn/) · [📐 Architecture](docs/architecture.md) · [📊 Evaluation](docs/evaluation.md) · [🎬 Video Demo](docs/video-demo.md) · [📋 Worklog](docs/worklog.md)

</div>

---

## 🖼️ Screenshots

![LitReview Agent — Landing Page](presentation/Screenshot%202026-09-01%20100431.png)

> *Giao diện landing page — PRISMA & Scopus Grounded SLR*

---

## 🎯 Vấn đề & Giải pháp

Các nhà nghiên cứu phải dành **hàng trăm giờ** đọc và phân loại bài báo thủ công cho mỗi Systematic Literature Review. LitReview Agent tự động hóa toàn bộ pipeline này:

- 🔍 **Tìm kiếm tự động** từ Google Scholar với Scopus Q1/Q2 verification
- 🤖 **AI Screening** — Gemini LLM đọc abstract và phân loại Include/Exclude theo criteria của bạn
- 📄 **RAG Chat** — trò chuyện trực tiếp với các bài báo PDF đã upload
- ✍️ **Synthesis tự động** — tạo literature review draft với citation grounded trên DOI thật
- 📤 **Export** sang Excel, BibTeX, CSV để dùng ngay trong Mendeley/Zotero

---

## 🤖 Tính năng Cốt lõi (6 Modules)

| # | Module | Mô tả |
|---|--------|-------|
| 1 | **Research Setup** | Định nghĩa câu hỏi nghiên cứu, PICO framework, tiêu chí Include/Exclude |
| 2 | **Search & Verify** | Tìm kiếm Google Scholar qua SerpApi, xác minh Scopus với 48K+ records offline |
| 3 | **AI Screening** | Gemini LLM sàng lọc bài báo theo criteria, trả về score 1-3 kèm lý do |
| 4 | **Quality Check** | Xác minh Journal Quartile (Q1-Q4) và Open Access status |
| 5 | **Workspace / RAG** | Upload PDF → ChromaDB embedding → Q&A chat với tài liệu |
| 6 | **Export & Citation** | Xuất Excel, BibTeX, CSV, Markdown — tương thích Mendeley/Zotero |

---

## 🏗️ Kiến trúc Hệ thống

Chi tiết sơ đồ kiến trúc, data flow và agent pipeline:  
**→ [docs/architecture.md](docs/architecture.md)**

**Tech Stack tóm tắt:**

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, Vite, TailwindCSS |
| **Backend** | Python 3.11, FastAPI, Uvicorn |
| **AI / Agents** | LangGraph, LangChain, Google Gemini 2.0 Flash |
| **Database** | PostgreSQL (relational) + ChromaDB (vector store) |
| **Search** | SerpApi (Google Scholar) + OpenAlex API (Scopus verify) |
| **Deploy** | AWS EC2 (backend) + Vercel (frontend) |

---

## 📁 Cấu trúc thư mục

```
P-165/
├── README.md                  # Deliverable #2
├── JOURNAL.md                 # Deliverable #8 — Development Journal
├── WORKLOG.md                 # Deliverable #9 — Commit history
├── Dockerfile                 # Docker build cho backend
├── docker-compose.yml         # Local dev stack (PostgreSQL + backend)
├── requirements.txt           # Python dependencies
├── .env.example               # Template biến môi trường
│
├── src/                       # Deliverable #1 — Backend source code
│   ├── main.py                # FastAPI app entrypoint
│   ├── config.py              # App configuration
│   ├── database.py            # PostgreSQL + SQLAlchemy setup
│   ├── api/                   # REST API routes
│   ├── agents/                # LangGraph agent definitions
│   ├── services/              # Business logic (search, screening, RAG)
│   ├── synthesis/             # Literature synthesis pipeline
│   └── models/                # Pydantic models
│
├── frontend/                  # Deliverable #1 — Frontend source code
│   ├── src/
│   │   ├── components/        # React components
│   │   └── App.jsx            # Main app component
│   └── package.json
│
├── tests/                     # Test suite (pytest)
├── benchmark/                 # Benchmark scripts & results CSV
├── eval/                      # RAGAS evaluation scripts & results
├── docs/                      # Tất cả deliverables docs
│   ├── architecture.md        # Deliverable #3 — System architecture
│   ├── ai-logs.md             # Deliverable #4 — LLM call traces (DB-backed)
│   ├── video-demo.md          # Deliverable #6 — Demo video link
│   ├── journal.md             # Deliverable #8 (copy)
│   ├── worklog.md             # Deliverable #9 (copy)
│   └── evaluation.md          # Deliverable #10 — Evaluation evidence
│
└── presentation/              # Pitch deck & screenshots
```

---


## 🚀 Cài đặt & Chạy (Quick Start)

### Yêu cầu
- Python 3.11+, Node.js 18+, Docker

### 1. Clone & Cài đặt Backend
```bash
git clone https://github.com/AI20K-Build-Phase-Cohort-3/P-165.git
cd P-165

python -m venv .venv
# Windows:  .\.venv\Scripts\Activate.ps1
# Mac/Linux: source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Cài đặt Database & Biến môi trường
```bash
docker compose up -d db      # Khởi động PostgreSQL ở cổng 5434
cp .env.example .env         # Tạo file .env
```

Mở `.env` và điền:
- `GEMINI_API_KEY` — từ [Google AI Studio](https://aistudio.google.com/)
- `AI_LOG_API_KEY` — tracking key từ AI20K

### 3. Khởi chạy
```bash
# Terminal 1 — Backend
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Frontend
cd frontend && npm install && npm run dev
```

Truy cập: **http://localhost:5173**

> 📘 Deploy lên cloud: xem [DEPLOY_GUIDE.md](DEPLOY_GUIDE.md) (Render + Vercel + Supabase)

---

## 🔑 Biến môi trường

| Variable | Required | Mô tả |
|----------|:--------:|-------|
| `GEMINI_API_KEY` | ✅ | API key Google AI Studio |
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `AI_LOG_API_KEY` | ✅ | AI20K tracking key |
| `LANGCHAIN_TRACING_V2` | — | LangSmith tracing — hiện bị tắt cứng trong `src/main.py`, xem [docs/ai-logs.md](docs/ai-logs.md) |
| `LANGCHAIN_API_KEY` | — | LangSmith API key (không dùng, xem trên) |
| `CORS_ORIGINS` | — | Frontend URL (mặc định: localhost:5173) |

---

## 🧪 Đánh giá (Evaluation Evidence)

| Metric | Kết quả |
|--------|---------|
| **Agent JSON Accuracy** (120 test cases) | **99.2%** |
| **PICO Schema Compliance** | **99.2%** |
| **RAG Faithfulness (RAGAS)** | **0.88** |
| **RAG Relevancy (RAGAS)** | **0.90** |
| **Synthesis Speed Improvement** | **5.56x nhanh hơn** (-82%) |
| **E2E Test Cases (manual)** | **5/5 Verified ✅** |

→ Xem chi tiết: **[docs/evaluation.md](docs/evaluation.md)**

---

## 📦 Deliverables

| # | Deliverable | Link |
|---|-------------|------|
| 1 | Source Code | Repo này |
| 2 | README | Bạn đang đọc |
| 3 | Architecture Diagram | [docs/architecture.md](docs/architecture.md) |
| 4 | AI Logs | [docs/ai-logs.md](docs/ai-logs.md) |
| 5 | Live URL | [c3-app-165.io.vn](https://www.c3-app-165.io.vn/) |
| 6 | Video Demo | [docs/video-demo.md](docs/video-demo.md) |
| 8 | Development Journal | [JOURNAL.md](JOURNAL.md) |
| 9 | Worklog | [docs/worklog.md](docs/worklog.md) |
| 10 | Evaluation Evidence | [docs/evaluation.md](docs/evaluation.md) |

---

## 👥 Team

**P-165 — AI Engineering Cohort 3, AI20K Build Phase**

| Họ và tên | MSSV | GitHub |
|-----------|------|--------|
| Nguyễn Đình Liêm | 2A202601421 | [@liemnd4](https://github.com/liemnd4) |
| Tạ Thị Nga | 2A202601125 | [@ngatt-17](https://github.com/ngatt-17) |
| Nguyễn Văn Hưng | 2A202601970 | [@lucasvahust](https://github.com/lucasvahust) |
| Nguyễn Đào Nam Hải | 2A202601037 | [@NamHaiIT2HUST](https://github.com/NamHaiIT2HUST) |

---

## 📄 License

MIT License — tự do sử dụng và tùy biến.
