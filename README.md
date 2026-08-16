<div align="center">

# 🤖 LitReview Agent

**AI-Powered Systematic Literature Review (SLR) System**

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain.com/)

</div>

LitReview Agent là một hệ thống AI đa tác vụ (Agentic Workflow) được thiết kế đặc biệt để hỗ trợ các nhà nghiên cứu trong quá trình Tổng quan Tài liệu Hệ thống (Systematic Literature Review). Hệ thống tự động hóa quá trình tìm kiếm, sàng lọc, đánh giá chất lượng và trích xuất thông tin từ các bài báo khoa học.

---

## 🏗️ Kiến trúc Hệ thống (Architecture)

Chi tiết sơ đồ kiến trúc và luồng dữ liệu vui lòng xem tại: [System Architecture & Data Flow](docs/architecture.md)

![Architecture Demo](https://raw.githubusercontent.com/langchain-ai/langgraph/main/docs/static/img/langgraph_logo.png) *(Hình minh họa LangGraph)*

---

## 🎯 Tính năng Cốt lõi (Modules)

Dự án được chia thành 6 module chính, tạo thành một quy trình SLR khép kín:

1. **Cấu hình (Research Setup)**: Định nghĩa câu hỏi nghiên cứu, tiêu chí loại trừ (Exclusion) và tiêu chí bao gồm (Inclusion).
2. **Tìm kiếm (Search & Verify)**: Tích hợp Google Scholar qua SerpApi, tự động đối chiếu và xác minh bài báo thuộc danh mục chuẩn (Scopus / Web of Science). Hỗ trợ chống trùng lặp.
3. **Sàng lọc AI (LLM Screening)**: Sử dụng Gemini đánh giá độ phù hợp của bài báo với tiêu chí nghiên cứu dựa trên Title và Abstract.
4. **Kiểm tra Chất lượng (Quality Check)**: Xác minh Journal Quartile (Q1-Q4) và trạng thái Open Access.
5. **Không gian làm việc (Workspace / RAG)**: Upload PDF toàn văn, trích xuất text tự động, và trò chuyện (Q&A) với tài liệu thông qua công nghệ RAG (Retrieval-Augmented Generation).
6. **Xuất dữ liệu (Export & Citation)**: Kết xuất dữ liệu ra Excel, BibTeX phục vụ việc viết bài báo hoặc import vào Mendeley/Zotero.

---

## 💻 Tech Stack

- **Frontend:** React, Vite, TailwindCSS (Vanilla CSS logic), React PDF.
- **Backend:** Python 3.11+, FastAPI.
- **AI / LLM Orchestration:** LangGraph, LangChain, Google Gemini (1.5 Flash).
- **Database:** PostgreSQL (Lưu trữ quan hệ) + ChromaDB (Vector Store cho RAG).
- **External APIs:** SerpApi (Scholar search), OpenAlex (Scopus verification).

---

## 🚀 Setup & Deploy (Quick Start)

### Yêu cầu hệ thống
- Python 3.11+
- Node.js 18+
- Docker (chạy PostgreSQL)

### 1. Clone dự án & Cài đặt Backend
```bash
git clone https://github.com/AI20K-Build-Phase-Cohort-3/P-165.git
cd P-165

# Tạo virtual environment
python -m venv .venv
# Kích hoạt venv (Windows): .\.venv\Scripts\Activate.ps1
# Kích hoạt venv (Mac/Linux): source .venv/bin/activate

# Cài đặt thư viện
pip install -r requirements.txt
```

### 2. Thiết lập Database & Biến môi trường
```bash
# Khởi động PostgreSQL ở cổng 5434
docker compose up -d db

# Khởi tạo file biến môi trường
cp .env.example .env
```
Mở file `.env` và điền key:
- `GEMINI_API_KEY`: API key từ Google AI Studio.
- `AI_LOG_API_KEY`: Key tracking của khóa học.

### 3. Khởi chạy
**Chạy Backend (Terminal 1):**
```bash
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

**Chạy Frontend (Terminal 2):**
```bash
cd frontend
npm install
npm run dev
```
Truy cập: `http://localhost:5173`

> 📘 **Hướng dẫn Deploy lên Cloud:** Xem chi tiết tại [DEPLOY_GUIDE.md](DEPLOY_GUIDE.md) để biết cách đưa lên Render, Supabase và Vercel.

---

## 🔑 Biến môi trường (Environment Variables)

Bảng các biến môi trường quan trọng (đặt trong `.env` backend):

| Variable | Description | Default / Example |
|----------|-------------|-------------------|
| `GEMINI_API_KEY` | Bắt buộc. Khóa API cho tính năng AI | `AIzaSy...` |
| `DATABASE_URL` | Chuỗi kết nối PostgreSQL | `postgresql://postgres:pass@localhost:5434/litreview` |
| `APP_ENV` | Chế độ chạy | `development` |
| `CORS_ORIGINS` | Allow list CORS cho frontend | `http://localhost:5173` |
| `AI_LOG_API_KEY` | Bắt buộc. Tracking khóa học AI20K | `ai20k_...` |

---

## 🔍 Sample Queries (Các truy vấn mẫu)

Để test khả năng tìm kiếm và sàng lọc (yêu cầu cấu hình SerpApi Key trên giao diện), bạn có thể thử các truy vấn sau:

1. **Y tế / Deep Learning:** `ECG signal analysis AND 1D models AND high accuracy`
2. **Blockchain:** `Blockchain technology in healthcare data privacy`
3. **AI / NLP:** `Large language models hallucination mitigation techniques`
4. **Năng lượng:** `Smart grid optimization using machine learning algorithms`
5. **Kinh tế:** `Impact of artificial intelligence on supply chain risk management`

---

## 🧪 Đánh giá (Eval Evidences)

Dự án đã được test thực tế (End-to-End). Xem chi tiết 5 manual test cases (tìm kiếm, sàng lọc, Q&A) tại: [Eval Evidences](docs/eval_evidence.md)

---

## 📄 License
MIT License. Tự do tùy biến và sử dụng.
