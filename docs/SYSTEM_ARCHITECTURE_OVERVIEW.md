# HỆ THỐNG KIẾN TRÚC TỔNG QUAN — LITERATURE REVIEW AI AGENT (P-165)
> **Cập nhật ngày:** 11/08/2026  
> **Phiên bản:** v2.0 (Evidence-Driven Multi-Agent Synthesis & Ingestion Provenance)

---

## 1. TỔNG QUAN HỆ THỐNG (SYSTEM OVERVIEW)

Hệ thống **AI20K Agent (P-165)** là một nền tảng hỗ trợ nghiên cứu học thuật cao cấp, được xây dựng theo kiến trúc **Multi-Agent / RAG nâng cao (Evidence-Driven)** chống ảo giác (Anti-hallucination).

Hệ thống bao gồm 2 Agent chính:
1. **Single-Turn Chat Agent (LangGraph)**: Xử lý hỏi đáp nhanh từng câu hỏi dựa trên các tài liệu đã tải lên với luồng `retrieve → guard → draft`.
2. **Deep Literature Review Synthesis Engine (LangGraph Map-Reduce)**: Xử lý tổng quan tài liệu chuyên sâu đa bài báo (Multi-Paper Synthesis) theo mô hình Map-Reduce bất đồng bộ qua **Celery + Redis**, trích xuất bằng chứng theo offset ký tự gốc (`page_char_start/end`) và tự động đối chiếu trích dẫn bằng mã (Code Citation Resolver).

---

## 2. SƠ ĐỒ KIẾN TRÚC TỔNG THỂ (SYSTEM ARCHITECTURE DIAGRAM)

```mermaid
flowchart TB
    subgraph Frontend["🎨 FRONTEND LAYER (React + Vite)"]
        UI["React SPA"]
        ST["SearchTab Component"]
        UT["UploadTab Component"]
        SP["SynthesisPanel Component"]
        CP["ChatPanel Component"]
    end

    subgraph API["🚀 API GATEWAY & BACKEND LAYER (FastAPI)"]
        Routes["FastAPI Router (/api/v1)"]
        ProjectRoutes["Project & Folder Routes"]
        ChatRoute["POST /api/v1/chat"]
        UploadRoute["POST /api/v1/workspace/upload"]
        SynthRoute["POST /api/v1/synthesis/sessions"]
    end

    subgraph Async["⚡ ASYNC JOB QUEUE (Celery + Redis)"]
        Redis[("Redis Broker & Result Backend")]
        CeleryWorker["Celery Worker Tasks"]
    end

    subgraph Agents["🧠 LANGGRAPH AGENT ENGINES"]
        subgraph ChatAgent["1. Chat RAG Agent Flow"]
            RetrieveNode["Retrieve Node\n(Vector Store Search)"]
            GuardNode["Integrity Guard Node\n(Crossref DOI Check)"]
            DraftNode["Draft Node\n(Structured RAG Answer)"]
        end

        subgraph SynthGraph["2. Map-Reduce Synthesis Graph Engine"]
            S_Start["Paper Fan-Out"]
            S_Retrieval["Chroma Anchor + PageText Window"]
            S_Evidence["Evidence Extraction & Retry"]
            S_Grounding["Grounding Service (Char Offsets)"]
            S_Claims["Cross-Paper Claims & Joint Verification"]
            S_Outline["Evidence-Driven Outline"]
            S_SectionFanOut["Section Fan-Out"]
            S_DraftSection["Section Drafting (Verified Claims)"]
            S_Resolver["Code Citation Resolver"]
        end
    end

    subgraph Storage["💾 STORAGE & DATABASE LAYER"]
        ChromaDB[("ChromaDB / Qdrant\n(Vector Store)")]
        SQLDB[("PostgreSQL / SQLite\n(Relational Database)")]
    end

    subgraph ExtServices["🌍 EXTERNAL SERVICES"]
        CrossrefAPI["Crossref REST API\n(Retraction Watch Check)"]
        OpenRouterLLM["OpenRouter / OpenAI LLM\n(gpt-4o-mini / llama-3.3-70b-free)"]
        HFEmbeddings["HuggingFace Embeddings\n(all-MiniLM-L6-v2 Local)"]
    end

    %% Connections
    UI --> ST & UT & SP & CP
    ST & UT & SP & CP --> Routes & ProjectRoutes
    ChatRoute --> ChatAgent
    SynthRoute --> Redis
    Redis --> CeleryWorker
    CeleryWorker --> SynthGraph

    RetrieveNode --> ChromaDB
    GuardNode --> CrossrefAPI
    DraftNode --> OpenRouterLLM

    S_Retrieval --> ChromaDB & SQLDB
    S_Evidence & S_Claims & S_DraftSection --> OpenRouterLLM
    S_Grounding --> SQLDB
    
    UploadRoute --> HFEmbeddings --> ChromaDB
    UploadRoute --> SQLDB
```

---

## 3. LUỒNG DỮ LIỆU TỔNG QUAN TÀI LIỆU CHUYÊN SÂU (SYNTHESIS DATAFLOW)

Luồng xử lý **Multi-Paper Synthesis** chạy theo mô hình **Map-Reduce / Send API của LangGraph**:

```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng (Frontend)
    participant API as FastAPI Backend
    participant Celery as Celery Worker + Redis
    participant Graph as LangGraph Synthesis Engine
    participant Guard as Integrity Guard & Crossref
    participant Vector as Vector DB & PageText Store
    participant LLM as OpenRouter / OpenAI LLM

    User->>API: 1. Gửi yêu cầu Synthesis (Selected Paper IDs + Topic)
    API->>Celery: 2. Đăng ký Long-running Task (Task ID)
    API-->>User: 3. Trả về Session ID (202 Accepted)
    
    loop Polling Tiến Độ (SynthesisPanel UI)
        User->>API: GET /api/v1/synthesis/sessions/{id}
        API-->>User: Trạng thái (status: RUNNING / PROGRESS)
    end

    activate Celery
    Celery->>Graph: 4. Khởi tạo StateGraph(SynthesisState)
    
    Note over Graph: 🚀 STEP A: PAPER FAN-OUT (MAP)
    Graph->>Guard: 5. Kiểm tra DOI từng bài qua Crossref
    Guard-->>Graph: Trả về trạng thái (Active / Retracted / Unknown)
    
    Graph->>Vector: 6. Tìm kiếm Anchor Chunks & Lấy raw PageText Cửa sổ trang
    Vector-->>Graph: Trả về chuỗi văn bản nguyên bản trang (PageText)
    
    Note over Graph: 🚀 STEP B: EVIDENCE EXTRACTION & GROUNDING
    Graph->>LLM: 7. Trích xuất mảng bằng chứng (Evidence Candidates)
    LLM-->>Graph: Trả về Evidence Candidate Quotes
    Graph->>Graph: 8. Chạy GroundingService (Khớp chính xác Offset char start/end)
    
    Note over Graph: 🚀 STEP C: CROSS-PAPER CLAIMS & OUTLINE
    Graph->>LLM: 9. Tổng hợp Claims chéo giữa các bài báo & Joint Verification
    LLM-->>Graph: Verified Claims
    Graph->>Graph: 10. Tạo Evidence-Driven Outline (Không tạo outline trước khi có bằng chứng)
    
    Note over Graph: 🚀 STEP D: SECTION FAN-OUT (MAP) & DRAFTING
    Graph->>LLM: 11. Viết từng Section dựa CHỈ trên Verified Claims (Chặn LLM tự chèn [1], [2])
    LLM-->>Graph: Section Drafts
    
    Note over Graph: 🚀 STEP E: CODE CITATION RESOLVER (REDUCE)
    Graph->>Graph: 12. Gắn Trích dẫn tự động bằng Code (Paper ID, Evidence ID, Page, Char Offsets)
    Graph->>Celery: 13. Hoàn tất Synthesis Review
    deactivate Celery

    Celery->>API: 14. Cập nhật DB (Status: COMPLETED)
    User->>API: 15. GET /api/v1/synthesis/sessions/{id}
    API-->>User: Trả về Literature Review hoàn chỉnh + Citation Markers
```

---

## 4. CHI TIẾT CÁC THÀNH PHẦN NÂNG CẤP CHÍNH (KEY COMPONENTS)

### 4.1. Ingestion Provenance & Data Traceability (`src/services/ingestion_service.py`)
- **PageText Storage**: Lưu nguyên văn bản thô của từng trang PDF (`page_number`, `raw_text`) vào cơ sở dữ liệu.
- **Canonical Chunk ID & Offsets**: Mỗi đoạn chunk được tạo ID duy nhất `canonical_chunk_id` kèm vị trí ký tự đầu/cuối chính xác (`page_char_start`, `page_char_end`).
- **Re-ingestion Safety**: Tách biệt việc tạo staging vector mới và dọn dẹp vector cũ, tránh tình trạng rollback DB làm mất dữ liệu.

### 4.2. Integrity Guard (`src/services/integrity_service.py` & `src/agents/nodes/guard_node.py`)
- Tra cứu real-time DOI qua Crossref API (`https://api.crossref.org/works/{doi}`).
- Tự động phát hiện các bài báo đã bị rút (**Retracted Paper**) và chặn lại trước khi đưa vào luồng tổng hợp.
- Trả về danh sách `blocked_sources` phục vụ công tác đánh giá an toàn (Safety Evaluation Evidence).

### 4.3. Grounding Service (`src/services/grounding_service.py`)
- Khớp trích dẫn bằng mã máy tính (Deterministic Code Matching) với cửa sổ ngữ cảnh `raw_text[n-1:n+1]`.
- Xử lý gạch nối xuống dòng của file PDF (PDF hyphenation) và khoảng trắng thừa.
- Cơ chế **Retry Grounding tối đa 2 lần** nếu phát hiện trích dẫn hỏng, không bỏ sót bằng chứng.

### 4.4. Code Citation Resolver & Strict Pydantic Control
- **Chặn LLM tự tiện bịa trích dẫn**: Pydantic schema chặn không cho LLM tự chèn kí hiệu trích dẫn dạng `[1]`, `[2]`.
- Trích dẫn được tính toán và gắn hoàn toàn bằng mã Python (`Citation Resolver`) dựa trên `Paper ID`, `Evidence ID`, `Page`, và `Char Offsets`.

---

## 5. CƠ SỞ DỮ LIỆU HỆ THỐNG (DATABASE SCHEMA)

```mermaid
erDiagram
    papers ||--o{ page_texts : "chứa"
    papers ||--o{ folder_papers : "thuộc"
    project_folders ||--o{ folder_papers : "quản lý"
    
    synthesis_sessions ||--o{ synthesis_reviews : "sinh ra"
    synthesis_sessions ||--o{ evidence_records : "thu thập"
    synthesis_sessions ||--o{ verified_claims : "xác minh"
    
    page_texts ||--o{ evidence_records : "trích xuất từ"

    papers {
        string id PK
        string title
        string authors
        int year
        string journal
        string doi
        string pdf_path
    }

    page_texts {
        string id PK
        string paper_id FK
        int page_number
        string raw_text
        string text_hash
    }

    synthesis_sessions {
        string id PK
        string topic
        string status
        json selected_paper_ids
        datetime created_at
    }

    evidence_records {
        string id PK
        string session_id FK
        string page_text_id FK
        string quote
        int char_start
        int char_end
        float confidence_score
    }

    synthesis_reviews {
        string id PK
        string session_id FK
        string final_text
        json citations_map
        datetime created_at
    }
```

---

## 6. QUẢN LÝ CẤU HÌNH & LINH HOẠT MODEL (CONFIG & HYBRID MODELS)

| Thành phần | Công nghệ / Model mặc định | Tùy chọn chuyển đổi linh hoạt |
|---|---|---|
| **Chat LLM** | `meta-llama/llama-3.3-70b-instruct:free` (via OpenRouter) | `gpt-4o-mini`, `gemini-2.0-flash-exp:free`, `deepseek-r1:free` |
| **Vector Embedding** | `sentence-transformers/all-MiniLM-L6-v2` (Local 100%) | `GoogleGenerativeAIEmbeddings` (`text-embedding-004`), `OpenAIEmbeddings` |
| **Vector Store** | `ChromaDB` (Embedded / Docker) | `Qdrant` |
| **Task Queue** | `Celery` + `Redis` | Synchronous Direct Invocation |
| **Relational DB** | `SQLite` (`./data/app.db`) | `PostgreSQL` |

---

## 7. QUY TRÌNH KIỂM THỬ VÀ XÁC NHẬN (VERIFICATION & TESTING)

1. **Biên dịch Python Syntax**:
   ```bash
   python -m compileall src/
   ```
   *Kết quả: OK 100% (0 lỗi syntax).*

2. **Kiểm tra Integrity Guard với DOI Retracted**:
   - Test DOI bị rút: `10.1002/cbic.202400798` $\rightarrow$ Trả về `status: retracted`.

3. **Kiểm tra Synthesis API**:
   - `POST /api/v1/workspace/upload`: Lưu PDF + bóc tách `PageText` chuẩn hóa.
   - `POST /api/v1/synthesis/sessions`: Đăng ký session Synthesis bất đồng bộ.
   - `GET /api/v1/synthesis/sessions/{id}`: Polling tiến độ và nhận kết quả Literature Review kèm `citations` chuẩn xác.
