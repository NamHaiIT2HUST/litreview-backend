# System Architecture & Data Flow

Dự án **LitReview Agent** được thiết kế theo kiến trúc Client-Server hiện đại, kết hợp với luồng xử lý AI (Agentic Workflow) sử dụng LangGraph để tự động hóa các tác vụ nghiên cứu.

## 1. High-Level Architecture

Sơ đồ dưới đây mô tả kiến trúc tổng thể, từ giao diện người dùng (Frontend) kết nối đến API Server (Backend), và tương tác với các external services (LLM, Search API).

```mermaid
graph TD
    %% Frontend Components
    subgraph Frontend ["Frontend (React + Vite)"]
        UI_Search[Search Interface]
        UI_Screening[AI Screening Board]
        UI_Chat[Chat/Q&A UI]
        UI_Config[Configuration Panel]
    end

    %% Backend Components
    subgraph Backend ["Backend (FastAPI + LangGraph)"]
        API_Routes[REST API Routes]
        Agent_Router[LangGraph Router]
        
        subgraph Modules ["Core Modules"]
            Mod_Search[Search Engine Integration]
            Mod_Screening[LLM Screening Pipeline]
            Mod_Extract[PDF Ingestion & Extraction]
            Mod_Chat[RAG Q&A Engine]
            Mod_Export[Export Generator]
        end
        
        API_Routes --> Agent_Router
        Agent_Router --> Modules
    end

    %% Storage Layer
    subgraph Storage ["Storage Layer"]
        DB[(PostgreSQL)]
        VectorDB[(ChromaDB)]
    end

    %% External Services
    subgraph External ["External Services (APIs)"]
        LLM[Google Gemini / OpenAI]
        SerpApi[SerpApi - Google Scholar]
        Scopus[Scopus/OpenAlex Validation]
    end

    %% Connections
    Frontend <==>|HTTP/REST| API_Routes
    Mod_Search <==> SerpApi
    Mod_Search <==> Scopus
    Mod_Screening <==> LLM
    Mod_Chat <==> LLM
    
    Modules <==> DB
    Mod_Extract ==> VectorDB
    Mod_Chat <==> VectorDB
```

---

## 2. Data Flow: Search & Verify Pipeline

Luồng xử lý khi người dùng thực hiện một truy vấn tìm kiếm mới. Trọng tâm của phase này là lấy đủ dữ liệu từ Google Scholar và xác minh tính hợp lệ (thuộc danh mục Scopus).

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API as FastAPI Backend
    participant SerpApi as SerpApi (Scholar)
    participant Scopus as OpenAlex/Scopus API
    participant DB as PostgreSQL

    User->>Frontend: Nhập query "ECG signal analysis"
    Frontend->>API: POST /api/v1/projects/{id}/search
    
    API->>SerpApi: Fetch papers (Pagination)
    SerpApi-->>API: Return raw papers (Title, Authors, Snippet)
    
    loop Sàng lọc Scopus
        API->>Scopus: Kiểm tra ISSN/Tên Tạp chí
        Scopus-->>API: Trạng thái Index (Có/Không)
        Note right of API: Tiếp tục fetch trang mới<br>nếu chưa đủ target (20 bài hợp lệ)
    end
    
    API->>DB: Lưu lịch sử Query
    API->>DB: Upsert Papers (chống trùng lặp)
    API->>DB: Liên kết Query <-> Paper (M-N)
    
    DB-->>API: Trả về kết quả đã lưu
    API-->>Frontend: Trả về danh sách 20 bài Scopus
    Frontend-->>User: Hiển thị giao diện kết quả
```

---

## 3. Data Flow: AI Screening

Quá trình sử dụng LLM để đánh giá mức độ phù hợp của bài báo đối với chủ đề nghiên cứu.

```mermaid
graph LR
    subgraph DB_State ["Database (Papers)"]
        P_Unscreened[Status: undetermined]
    end

    subgraph LLM_Pipeline ["LangChain / LangGraph Pipeline"]
        Prompt_Builder[Build Prompt with<br>Title + Abstract + Criteria]
        LLM_Model[Gemini Flash 1.5]
        Parser[Pydantic Output Parser]
    end
    
    P_Unscreened --> Prompt_Builder
    Prompt_Builder --> LLM_Model
    LLM_Model --> Parser
    
    Parser --> |Score: 1| P_Exclude[Status: excluded]
    Parser --> |Score: 2-3| P_Include[Status: included]
    
    P_Exclude --> DB_State
    P_Include --> DB_State
```

---

## 4. RAG Chat & Synthesis Architecture

Luồng xử lý Q&A với tài liệu PDF đã upload.

```mermaid
graph TD
    subgraph Ingestion
        PDF[User Uploads PDF]
        PyMuPDF[Text Extraction]
        Chunker[Text Splitter]
        Embedder[Embedding Model]
        
        PDF --> PyMuPDF --> Chunker --> Embedder --> VectorDB[(ChromaDB)]
    end
    
    subgraph Query
        User_Q[User Question]
        Retriever[Vector Similarity Search]
        Generator[LLM Synthesis]
        
        User_Q --> Retriever
        Retriever -->|Fetch Chunks| VectorDB
        VectorDB -->|Top K Chunks| Generator
        User_Q --> Generator
        Generator --> Answer[Final Answer + Citations]
    end
```
