# 🚀 Hướng dẫn chạy & deploy LitReview Agent

## Mục lục
- [Phần 1: Chạy Local](#phần-1-chạy-local-trên-máy-tính)
- [Phần 2: Deploy Supabase (Database)](#phần-2-deploy-supabase-database)
- [Phần 3: Deploy Render (Backend)](#phần-3-deploy-render-backend)
- [Phần 4: Deploy Vercel (Frontend)](#phần-4-deploy-vercel-frontend)
- [Tham khảo biến môi trường](#tham-khảo-biến-môi-trường)

---

## Phần 1: Chạy Local trên máy tính

### Yêu cầu
- **Python** >= 3.11
- **Node.js** >= 18
- **Docker Desktop** (để chạy PostgreSQL)
- **Git**

### Bước 1: Clone repo & cài đặt

```bash
git clone https://github.com/AI20K-Build-Phase-Cohort-3/P-165.git
cd P-165
```

**Backend (Python):**
```bash
python -m venv .venv

# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Windows Git Bash:
source .venv/Scripts/activate

pip install -r requirements.txt
```

**Frontend (Node.js):**
```bash
cd frontend
npm install
cd ..
```

### Bước 2: Khởi động PostgreSQL bằng Docker

```bash
docker compose up -d db
```

Lệnh này tạo container PostgreSQL trên **port 5434** (tránh trùng port 5432 mặc định).

> Kiểm tra container đang chạy:
> ```bash
> docker ps
> ```
> Phải thấy container `litreview-db` ở trạng thái `healthy`.

### Bước 3: Tạo file `.env`

```bash
cp .env.example .env
```

Mở file `.env` và điền các giá trị:

```env
# ---- LLM (bắt buộc để Search/Synthesis hoạt động) ----
GEMINI_API_KEY=your_gemini_api_key_here

# ---- Database (PostgreSQL trên Docker, port 5434) ----
DATABASE_URL=postgresql://postgres:password@localhost:5434/litreview

# ---- App Config ----
APP_ENV=development

# ---- AI Log (khóa tracking khóa học) ----
AI_LOG_SERVER=https://ai-logs.note.transformerlabs.ai/api/ingest
AI_LOG_API_KEY=your_ai_log_key_here
```

### Bước 4: Chạy Backend

```bash
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend sẽ:
1. Tự động tạo tất cả bảng trong PostgreSQL
2. Chạy migration bổ sung nếu schema thiếu cột
3. Seed default project

> ✅ Kiểm tra: mở trình duyệt truy cập `http://localhost:8000/health`
> Kết quả: `{"status": "ok", ...}`

### Bước 5: Chạy Frontend

```bash
cd frontend
npm run dev
```

> ✅ Mở trình duyệt: `http://localhost:5173`

### Bước 6: Sử dụng

1. Vào tab **Cấu hình** → nhập Khóa API SerpApi (lấy tại [serpapi.com](https://serpapi.com))
2. Vào tab **Tìm kiếm** → nhập từ khóa → nhấn **Tìm kiếm**
3. Hệ thống sẽ tìm 60 bài từ Google Scholar → đối chiếu Scopus → trả về 20 bài chất lượng nhất

---

## Phần 2: Deploy Supabase (Database)

Supabase cung cấp PostgreSQL miễn phí trên cloud, thay thế Docker local.

### Bước 1: Tạo tài khoản & project

1. Truy cập [https://supabase.com](https://supabase.com) → **Start your project**
2. Đăng nhập bằng GitHub
3. Nhấn **New Project**:
   - **Organization**: Chọn org cá nhân
   - **Project name**: `litreview-agent`
   - **Database Password**: Tạo mật khẩu mạnh (LƯU LẠI!)
   - **Region**: `Southeast Asia (Singapore)` — gần VN nhất
4. Nhấn **Create new project** → chờ ~2 phút

### Bước 2: Lấy Connection String

1. Vào **Project Settings** (biểu tượng ⚙️ bên trái)
2. Chọn **Database**
3. Mục **Connection string** → chọn tab **URI**
4. Copy chuỗi kết nối, có dạng:
   ```
   postgresql://postgres.[ref]:[PASSWORD]@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres
   ```
5. Thay `[PASSWORD]` bằng mật khẩu bạn đã tạo ở trên
6. **Quan trọng:** Thêm `?sslmode=require` vào cuối:
   ```
   postgresql://postgres.[ref]:YourPassword@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require
   ```

> ⚠️ **Lưu ý:** Chuỗi này sẽ được dùng làm `DATABASE_URL` cho Render backend.

---

## Phần 3: Deploy Render (Backend)

Render cho phép chạy backend Python miễn phí (free tier).

### Bước 1: Tạo tài khoản Render

1. Truy cập [https://render.com](https://render.com) → **Get Started**
2. Đăng nhập bằng GitHub

### Bước 2: Tạo Web Service

1. Nhấn **New** → **Web Service**
2. Chọn **Build and deploy from a Git repository** → **Next**
3. Kết nối repo:
   - Vì **bạn không phải owner**, chọn **Public Git repository**
   - Nhập URL: `https://github.com/AI20K-Build-Phase-Cohort-3/P-165.git`
   - Hoặc nếu Render đã kết nối GitHub org, chọn repo `P-165` từ danh sách
4. Cấu hình:
   - **Name**: `litreview-backend`
   - **Region**: `Singapore`
   - **Branch**: `main`
   - **Runtime**: `Docker`
   - **Instance Type**: `Free` (hoặc Starter nếu muốn nhanh hơn)

### Bước 3: Thiết lập Environment Variables

Vào **Environment** → thêm các biến sau:

| Key | Value |
|-----|-------|
| `DATABASE_URL` | `postgresql://postgres.[ref]:YourPassword@aws-0-...supabase.com:6543/postgres?sslmode=require` |
| `GEMINI_API_KEY` | Khóa Gemini của bạn |
| `GEMINI_API_KEYS` | (Tùy chọn) Nhiều khóa cách nhau bằng dấu phẩy |
| `APP_ENV` | `development` |
| `CORS_ORIGINS` | `https://your-vercel-app.vercel.app,http://localhost:5173` |
| `AI_LOG_SERVER` | `https://ai-logs.note.transformerlabs.ai/api/ingest` |
| `AI_LOG_API_KEY` | Khóa AI Log của bạn |
| `CHROMA_PERSIST_DIR` | `./data/chroma` |

> ⚠️ **`APP_ENV=development`** giúp chạy synthesis worker qua FastAPI BackgroundTasks,
> không cần Redis/Celery → **tiết kiệm tài nguyên, chạy được trên free tier.**

### Bước 4: Deploy

1. Nhấn **Create Web Service**
2. Render sẽ build Docker image và deploy tự động
3. Sau ~5 phút, bạn sẽ có URL dạng: `https://litreview-backend.onrender.com`

> ✅ Kiểm tra: truy cập `https://litreview-backend.onrender.com/health`

---

## Phần 4: Deploy Vercel (Frontend)

Vì bạn **không phải owner repo**, sử dụng **Vercel CLI** qua Git Bash.

### Bước 1: Cài đặt Vercel CLI

Mở **Git Bash** (hoặc Terminal):

```bash
npm install -g vercel
```

### Bước 2: Login Vercel

```bash
vercel login
```

Chọn phương thức đăng nhập (GitHub / Email). Làm theo hướng dẫn trên màn hình.

### Bước 3: Build Frontend

```bash
cd frontend
```

Tạo file `.env.production` trong thư mục `frontend/`:

```bash
echo 'VITE_API_BASE=https://litreview-backend.onrender.com/api/v1' > .env.production
```

> ⚠️ Thay `litreview-backend.onrender.com` bằng URL Render thực tế của bạn.

### Bước 4: Deploy lên Vercel

```bash
vercel --prod
```

Trả lời các câu hỏi:
- **Set up and deploy?** → `Y`
- **Which scope?** → Chọn tài khoản cá nhân của bạn
- **Link to existing project?** → `N`
- **What's your project's name?** → `litreview-agent` (hoặc tên tùy ý)
- **In which directory is your code located?** → `./` (thư mục frontend hiện tại)
- **Want to modify these settings?** → `N`

Vercel sẽ tự detect Vite, build và deploy. Sau khi hoàn tất, bạn nhận được URL dạng:
```
https://litreview-agent.vercel.app
```

### Bước 5: Thiết lập Environment Variable trên Vercel Dashboard

1. Truy cập [vercel.com/dashboard](https://vercel.com/dashboard) → chọn project vừa tạo
2. Vào **Settings** → **Environment Variables**
3. Thêm biến:

| Key | Value | Environment |
|-----|-------|-------------|
| `VITE_API_BASE` | `https://litreview-backend.onrender.com/api/v1` | Production |

4. Nhấn **Save**
5. Vào tab **Deployments** → **Redeploy** lần cuối để áp dụng biến mới

### Bước 6: Cập nhật CORS trên Render

Quay lại Render Dashboard → Environment Variables → cập nhật `CORS_ORIGINS`:

```
https://litreview-agent.vercel.app,http://localhost:5173
```

> Thay `litreview-agent.vercel.app` bằng URL Vercel thực tế.

---

## Tham khảo biến môi trường

### Backend (.env cho Render)

```env
# === BẮT BUỘC ===
DATABASE_URL=postgresql://...@supabase.com:6543/postgres?sslmode=require
GEMINI_API_KEY=your_key
APP_ENV=development
CORS_ORIGINS=https://your-app.vercel.app,http://localhost:5173

# === AI LOG (Tracking khóa học) ===
AI_LOG_SERVER=https://ai-logs.note.transformerlabs.ai/api/ingest
AI_LOG_API_KEY=your_ai_log_key

# === TÙY CHỌN ===
MODEL_NAME=gemini-1.5-flash
SYNTHESIS_LLM_PROVIDER=gemini
SYNTHESIS_MODEL=gemini-3.5-flash-lite
SYNTHESIS_TEMPERATURE=0.0
EMBEDDING_MODEL=text-embedding-004
CHROMA_PERSIST_DIR=./data/chroma
LOG_LEVEL=INFO
```

### Frontend (.env.production cho Vercel)

```env
VITE_API_BASE=https://litreview-backend.onrender.com/api/v1
```

---

## Lưu ý quan trọng

1. **Free tier Render** sẽ ngủ sau 15 phút không hoạt động. Lần truy cập đầu tiên sẽ mất ~30s để "thức dậy".
2. **Supabase free tier** cho phép 500MB database, 1GB bandwidth — đủ cho demo và testing.
3. **SerpApi key** cần nhập trên giao diện web (tab Cấu hình) — KHÔNG cần đặt trong biến môi trường server.
4. **Sau mỗi lần push code lên `main`**, Render sẽ tự động rebuild & redeploy. Vercel CLI cần chạy `vercel --prod` lại hoặc cấu hình auto-deploy qua dashboard.
