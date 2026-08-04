from fastapi import APIRouter, HTTPException, Query, Header
from typing import Optional

from src.agents.graph import agent
from src.models.schemas import ChatRequest, ChatResponse, SearchResponse
from src.services.scholar_api import search_papers_auto

router = APIRouter()

@router.get("/search", response_model=SearchResponse)
async def search_papers(
    query: str = Query(..., description="Từ khóa tìm kiếm"),
    x_api_key: Optional[str] = Header(None, description="SerpApi hoặc Semantic Scholar Key"),
    provider: Optional[str] = Query("auto", description="Nguồn dữ liệu: auto, serpapi, semanticscholar")
) -> SearchResponse:
    """Tra cứu bài báo học thuật thông qua external API (Hỗ trợ cả SerpApi & Semantic Scholar)."""
    if not x_api_key and provider != "auto":
        raise HTTPException(status_code=401, detail="X-API-Key header is missing")
    
    papers = await search_papers_auto(query=query, api_key=x_api_key or "", provider=provider, limit=10)
    return SearchResponse(papers=papers)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Chat với AI agent."""
    try:
        result = await agent.ainvoke({"query": request.message})
        return ChatResponse(
            response=result.get("response", ""),
            analysis=result.get("analysis", ""),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def agent_status():
    """Kiểm tra trạng thái agent."""
    return {"status": "ready", "agent": "LangGraph Agent v1.0"}
