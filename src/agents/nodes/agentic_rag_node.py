import asyncio
import os
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from src.agents.state import AgentState
from src.services.rag_service import rag_service
from src.services.vector_store import vector_store_service


# --- MAIN NODE WRAPPER ---

async def agentic_rag_node(state: AgentState) -> dict:
    """Node này đóng vai trò bọc Agentic RAG để chạy trong LangGraph chính."""
    query = state.get("query", "")
    if not query:
        return {"error": "Thiếu query."}

    paper_ids = state.get("paper_ids")

    # --- TOOLS FOR AGENTIC RAG (Closure) ---
    @tool
    async def search_and_extract_evidence(search_query: str, original_question: str) -> str:
        """Tìm kiếm tài liệu trong cơ sở dữ liệu và trích xuất các bằng chứng (evidence) liên quan.
        Sử dụng tool này khi bạn cần tìm thêm thông tin để trả lời câu hỏi.
        
        Args:
            search_query: Từ khóa hoặc câu truy vấn dùng để tìm kiếm tài liệu (vector search).
            original_question: Câu hỏi gốc của người dùng để hệ thống biết cần trích xuất thông tin gì từ tài liệu.
        """
        # Determine filters
        filters = None
        if paper_ids:
            if len(paper_ids) == 1:
                filters = {"paper_id": paper_ids[0]}
            else:
                filters = {"paper_id": {"$in": paper_ids}}

        # 1. Search ChromaDB
        chunks = await vector_store_service.search_similar_documents(search_query, top_k=10, filters=filters)
        if not chunks:
            return f"Không tìm thấy tài liệu nào với từ khóa: '{search_query}'"

        # 2. Extract Evidence (MAP step inspired by PaperQA2)
        tasks = []
        key_to_meta = {}
        
        for i, doc in enumerate(chunks):
            ckey = rag_service.make_citation_key(doc, i)
            if ckey in key_to_meta:
                ckey = f"{ckey}_{i}"
                
            source = doc.metadata.get("source", "unknown")
            page = str(doc.metadata.get("page", "?"))
            paper_title = rag_service._get_paper_title(doc)
            
            key_to_meta[ckey] = {
                "source": source,
                "page": page,
                "paper_title": paper_title,
            }
            
            tasks.append(rag_service._map_chunk(
                ckey,
                os.path.basename(str(source)),
                paper_title,
                page,
                doc.page_content,
                original_question,
            ))

        map_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 3. Filter and Format
        scored = []
        errors = []
        for item in map_results:
            if isinstance(item, Exception):
                errors.append(str(item))
                continue
            ckey, summary = item
            if summary.relevance_score >= 2 and summary.summary.strip(): # MIN_RELEVANCE_SCORE = 2
                scored.append((ckey, summary))
        
        if errors and not scored:
            # All chunks failed with exceptions (e.g. RateLimitError)
            return f"Lỗi trích xuất (có thể do Rate Limit API). Lỗi đầu tiên: {errors[0]}"

        scored.sort(key=lambda x: x[1].relevance_score, reverse=True)
        scored = scored[:5] # Top 5 relevant chunks per search

        if not scored:
            return f"Tìm thấy tài liệu cho '{search_query}' nhưng không có thông tin nào liên quan đến câu hỏi gốc."

        context_lines = []
        for ckey, cs in scored:
            meta = key_to_meta[ckey]
            page_display = int(meta["page"]) + 1 if str(meta["page"]).isdigit() else meta["page"]
            context_lines.append(
                f"[{ckey}] (Paper: {meta['paper_title']}, page {page_display}) - Độ liên quan: {cs.relevance_score}/10:\n{cs.summary}"
            )
            
        return "\n\n".join(context_lines)


    # --- AGENTIC RAG SUB-GRAPH SETUP ---
    llm = rag_service.llm
    tools = [search_and_extract_evidence]
    
    system_prompt = (
        "Bạn là một chuyên gia nghiên cứu phân tích chuyên sâu (Agentic RAG).\n"
        "Nhiệm vụ của bạn là trả lời câu hỏi của người dùng một cách toàn diện và chính xác nhất.\n"
        "Bạn CÓ THỂ gọi tool 'search_and_extract_evidence' NHIỀU LẦN với các 'search_query' khác nhau "
        "để thu thập đủ góc nhìn, bằng chứng, hoặc tìm ra 'research gap' (lỗ hổng nghiên cứu).\n\n"
        "QUY TẮC:\n"
        "1. Luôn sử dụng tool để tìm kiếm thông tin trước khi trả lời.\n"
        "2. Nếu thông tin tìm được chưa đủ, hãy thay đổi 'search_query' và tìm kiếm tiếp.\n"
        "3. Khi đã có đủ thông tin, hãy tổng hợp thành một câu trả lời chi tiết, có cấu trúc tốt (dùng Markdown, Bullet points).\n"
        "4. BẮT BUỘC phải trích dẫn nguồn ở cuối mỗi câu luận điểm dựa trên các [key] được cung cấp từ tool "
        "(Ví dụ: ...phương pháp này hiệu quả [paper_p3]).\n"
        "5. Viết câu trả lời bằng cùng ngôn ngữ với câu hỏi của người dùng."
    )
    
    agent_app = create_react_agent(llm, tools, state_modifier=system_prompt)
    
    # Chạy agent với recursion limit nhỏ để tránh treo loop quá lâu
    inputs = {"messages": [HumanMessage(content=query)]}
    try:
        result = await agent_app.ainvoke(inputs, config={"recursion_limit": 5})
        final_message = result["messages"][-1].content
        return {
            "response": final_message,
            "citations": []  # Hiện tại AgenticRAG đang nhúng citation [key] trực tiếp vào text
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"response": f"Lỗi nội bộ Agentic RAG: {str(e)}"}
