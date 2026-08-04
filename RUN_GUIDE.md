# 🚀 Hướng Dẫn Chạy Dự Án LitReview Agent

Tài liệu hướng dẫn khởi chạy chi tiết cho cả **Backend (FastAPI)** và **Frontend (Vite + React)**.

---

## 📋 Yêu cầu Tiền đề (Prerequisites)

- **Node.js**: v18+ (Khuyên dùng v20+)
- **Python**: v3.11+
- **Git**

---

## 🛠️ 1. Hướng dẫn Chạy Backend (FastAPI)

### Bước 1: Mở Terminal tại thư mục gốc của dự án
```bash
cd "P-165"
```

### Bước 2: Kích hoạt Môi trường ảo (Virtual Environment)
- **Trên Windows (PowerShell):**
  ```powershell
  .venv\Scripts\activate.ps1
  ```
- **Trên Windows (Git Bash / MINGW64):**
  ```bash
  source .venv/Scripts/activate
  ```
- **Trên macOS / Linux:**
  ```bash
  source .venv/bin/activate
  ```

*(Khi kích hoạt thành công, bạn sẽ thấy ký tự `(.venv)` xuất hiện ở đầu dòng lệnh).*

### Bước 3: Khởi chạy Server Backend
```bash
uvicorn src.main:app --reload
```
Server Backend sẽ chạy tại: **`http://localhost:8000`**  
Trang tài liệu API tự động (Swagger UI): **`http://localhost:8000/docs`**

---

## 🎨 2. Hướng dẫn Chạy Frontend (Vite + React)

### Bước 1: Mở một Terminal mới và di chuyển vào thư mục `frontend`
```bash
cd frontend
```

### Bước 2: Cài đặt Dependencies (nếu chưa cài)
```bash
npm install
```

### Bước 3: Chạy Frontend ở môi trường Development
```bash
npm run dev
```
Giao diện sẽ chạy tại: **`http://localhost:5173`** (hoặc port được cấp).

---

## 🔑 3. Hướng dẫn Sử dụng Tính năng Tra cứu (BYOK API Key)

Hệ thống hỗ trợ cơ chế **Bring Your Own Key (BYOK)** để người dùng tự cấp API Key:

1. **Các loại API Key được hỗ trợ:**
   - **SerpApi (Google Scholar Key):** Lấy miễn phí tại [serpapi.com/users/sign_up](https://serpapi.com/users/sign_up).
   - **Semantic Scholar Key (S2 Key):** Lấy miễn phí tại [semanticscholar.org/product/api](https://www.semanticscholar.org/product/api) (Key bắt đầu bằng `s2k-...`).

2. **Cách sử dụng:**
   - Mở giao diện web ở Tab **Tra cứu**.
   - Dán chuỗi API Key của bạn vào ô **API Key (SerpApi / S2 Key)** ở đầu trang.
   - Nhập từ khóa nghiên cứu (ví dụ: `deep learning in medical imaging`) và bấm **Tìm bài báo**.
   - Hệ thống sẽ tự động gọi API thật, phân tích số trích dẫn và hiển thị danh sách bài báo kèm điểm uy tín **LitScore (0-100)**!

---

## 📦 4. Cấu trúc Dự án (Project Layout)

```text
P-165/
├── src/                    # Backend FastAPI
│   ├── api/                # API Routes (/search, /chat, /status)
│   ├── models/             # Pydantic Schemas (Paper, ChatRequest)
│   ├── services/           # External API Service (SerpApi & Semantic Scholar)
│   └── main.py             # FastAPI App Entry & CORS Configuration
├── frontend/               # Frontend React Application
│   ├── src/
│   │   ├── components/     # UI Components (search, workspace, home...)
│   │   └── App.jsx         # Main App Component
│   └── package.json
├── RUN_GUIDE.md            # Tài liệu hướng dẫn này
└── requirements.txt        # Thư viện Python
```
