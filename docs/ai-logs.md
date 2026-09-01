# 🤖 AI Logs — LangSmith Traces

Tài liệu này ghi lại các trace của AI agent pipeline thông qua **LangSmith**, chứng minh hệ thống hoạt động đúng và có thể trace được.

---

## ⚙️ Cấu hình LangSmith

| Thông số | Giá trị |
|----------|---------|
| **Project** | `P-165-LitReview` |
| **Dashboard** | https://smith.langchain.com/ |
| **Env vars** | `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT` |

LangSmith tự động ghi lại mọi lần LangChain/LangGraph thực thi — không cần code thêm. Mỗi lần người dùng sử dụng app tại [https://www.c3-app-165.io.vn/](https://www.c3-app-165.io.vn/), trace sẽ được gửi lên dashboard.

---

## 📌 Cách lấy screenshot

1. Truy cập [smith.langchain.com](https://smith.langchain.com/) → chọn project **P-165-LitReview**
2. Chọn một run trace bất kỳ (AI Screening, RAG Chat, hoặc Research Setup)
3. Screenshot toàn bộ trace tree (hiển thị các node LangGraph, input/output)
4. Paste ảnh vào các section bên dưới

---

## 🔍 Trace mẫu — AI Screening Pipeline

> Trace này ghi lại luồng khi người dùng bấm "Sàng lọc AI" trên một bài báo.  
> Agent nhận `title + abstract + criteria` → Gemini LLM đánh giá → trả về `{decision, score, reasoning}`.

<!-- TODO: Paste screenshot LangSmith trace tại đây -->

---

## 🔍 Trace mẫu — RAG Q&A Pipeline

> Trace này ghi lại luồng khi người dùng chat với PDF trong tab "Chat with Sources".  
> ChromaDB retrieval → context assembly → Gemini generation → answer with citations.

<!-- TODO: Paste screenshot LangSmith trace tại đây -->

---

## 🔍 Trace mẫu — Research Setup Agent (PICO Extraction)

> Trace này ghi lại luồng khi agent phân tích câu hỏi nghiên cứu và trích xuất PICO framework.

<!-- TODO: Paste screenshot LangSmith trace tại đây -->
