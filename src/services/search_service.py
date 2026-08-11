import os
import json
import httpx
from typing import List
from fastapi import HTTPException
from src.services.rag_service import rag_service
from src.models.search_schemas import SearchStrategy

async def get_serpapi_count(query: str, api_key: str) -> int:
    """Gọi SerpAPI với num=1 để lấy tổng số kết quả dự kiến (count_only)."""
    if not api_key:
        return 0
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_scholar",
        "q": query,
        "api_key": api_key,
        "num": 1,
        "hl": "en"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                search_info = data.get("search_information", {})
                return search_info.get("total_results", 0)
        except Exception:
            pass
    return 0

async def generate_search_strategies(
    research_question: str, 
    research_field: str,
    criteria_include: List[str],
    criteria_exclude: List[str],
    api_key: str
) -> List[SearchStrategy]:
    """Sinh các boolean queries từ LLM và tính count thực tế từ SerpAPI."""
    prompt = f"""
    Bạn là một chuyên gia nghiên cứu tài liệu học thuật. Dựa trên thông tin dưới đây, hãy tạo ra 3 chiến lược tìm kiếm (boolean queries) để dùng trên Google Scholar.
    
    Lĩnh vực: {research_field}
    Research Question: {research_question}
    Inclusion Criteria: {', '.join(criteria_include) if criteria_include else 'None'}
    Exclusion Criteria: {', '.join(criteria_exclude) if criteria_exclude else 'None'}
    
    Yêu cầu:
    - Trả về CHỈ một mảng JSON các object, không có markdown formatting hay text nào khác.
    - Mỗi object có định dạng: {{"label": "Tên chiến lược", "query_string": "boolean query string"}}
    - query_string sử dụng các toán tử AND, OR, dấu ngoặc () và dấu ngoặc kép "" để tìm kiếm chính xác. KHÔNG thêm các từ khóa không cần thiết.
    """
    
    try:
        response = await rag_service.llm.ainvoke(prompt)
        content = response.content
        if isinstance(content, list):
            content = content[0].get("text", "")
        content = content.strip()
        
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()
            
        strategies_data = json.loads(content)
    except Exception as e:
        print(f"Error parsing LLM output: {e}")
        # Fallback strategy
        strategies_data = [
            {"label": "Broad Search", "query_string": f'"{research_question}"'}
        ]
        
    strategies = []
    for s in strategies_data[:3]: # Giới hạn 3 strategy
        query = s.get("query_string", "")
        label = s.get("label", "Strategy")
        count = await get_serpapi_count(query, api_key)
        strategies.append(SearchStrategy(label=label, query_string=query, result_count=count))
        
    return strategies
