import httpx
import datetime
import hashlib
import re
from typing import List
from fastapi import HTTPException
from src.models.schemas import Paper

def calculate_litscore(citations: int, year: int) -> int:
    """Tính điểm uy tín LitScore dựa trên trích dẫn và năm xuất bản."""
    current_year = datetime.datetime.now().year
    age = current_year - year
    if age < 0:
        age = 0
    
    age_penalty = age * 2
    citation_bonus = min(citations / 5, 50)  # max 50 points bonus
    score = 70 - age_penalty + citation_bonus
    return int(max(10, min(100, score)))

async def search_papers_semanticscholar(query: str, api_key: str = None, limit: int = 10) -> List[Paper]:
    """Search for papers using Semantic Scholar (S2) Graph API."""
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "paperId,title,authors,year,abstract,citationCount,openAccessPdf,externalIds"
    }
    
    headers = {}
    if api_key and api_key.strip():
        headers["x-api-key"] = api_key.strip()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, headers=headers, timeout=15.0)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                raise HTTPException(status_code=401, detail="Invalid Semantic Scholar API Key")
            elif e.response.status_code == 429:
                raise HTTPException(status_code=429, detail="Semantic Scholar API đang bị giới hạn số lượt request (429 Rate Limit). Vui lòng thử lại sau 1-2 phút hoặc dùng SerpApi Key.")
            raise HTTPException(status_code=500, detail=f"Semantic Scholar API error: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")

    results = data.get("data", [])
    papers = []
    
    for res in results:
        paper_id = res.get("paperId", "")
        title = res.get("title", "Unknown Title")
        
        # Format authors
        raw_authors = res.get("authors", [])
        author_names = [a.get("name", "") for a in raw_authors if a.get("name")]
        authors_str = ", ".join(author_names[:4]) if author_names else "Unknown Authors"
        if len(author_names) > 4:
            authors_str += " et al."
            
        year = res.get("year") or datetime.datetime.now().year
        abstract = res.get("abstract") or "No abstract provided."
        citations = res.get("citationCount") or 0
        
        # PDF URL
        pdf_info = res.get("openAccessPdf") or {}
        url_link = pdf_info.get("url") if isinstance(pdf_info, dict) else None
        if not url_link:
            url_link = f"https://www.semanticscholar.org/paper/{paper_id}"

        # DOI
        ext_ids = res.get("externalIds") or {}
        doi = ext_ids.get("DOI", "N/A") if isinstance(ext_ids, dict) else "N/A"
        
        paper = Paper(
            id=f"S2_{paper_id[:10]}",
            title=title,
            authors=authors_str,
            year=int(year),
            abstract=abstract,
            journal="Semantic Scholar",
            doi=doi,
            url=url_link,
            citations=int(citations),
            litScore=calculate_litscore(int(citations), int(year)),
            tldr=None
        )
        papers.append(paper)
        
    return papers

async def search_papers_serpapi(query: str, api_key: str, limit: int = 10) -> List[Paper]:
    """Search for papers using SerpApi (Google Scholar)."""
    if not api_key:
        raise HTTPException(status_code=401, detail="API Key is required for SerpApi")
        
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_scholar",
        "q": query,
        "api_key": api_key,
        "num": limit,
        "hl": "en"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=15.0)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid SerpApi Key or unauthorized")
            raise HTTPException(status_code=500, detail=f"External API error: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")
        
    results = data.get("organic_results", [])
    papers = []
    
    for res in results:
        title = res.get("title", "Unknown Title")
        pub_info = res.get("publication_info", {})
        summary = pub_info.get("summary", "")
        
        authors = summary.split("-")[0].strip() if "-" in summary else "Unknown Authors"
        year_match = re.search(r'\b(19|20)\d{2}\b', summary)
        year = int(year_match.group()) if year_match else datetime.datetime.now().year
        
        abstract = res.get("snippet", "No abstract available.")
        journal = "Google Scholar"
        url_link = res.get("link", "#")
        
        inline_links = res.get("inline_links", {})
        cited_by = inline_links.get("cited_by", {})
        citations = cited_by.get("total", 0) if isinstance(cited_by, dict) else 0
        
        paper_id = hashlib.md5(title.encode()).hexdigest()[:10]
        
        paper = Paper(
            id=f"GS_{paper_id}",
            title=title,
            authors=authors,
            year=year,
            abstract=abstract,
            journal=journal,
            doi="N/A",
            url=url_link,
            citations=citations,
            litScore=calculate_litscore(citations, year),
            tldr=None
        )
        papers.append(paper)
        
    return papers

async def search_papers_auto(query: str, api_key: str = None, provider: str = "auto", limit: int = 10) -> List[Paper]:
    """Auto-detect provider or use specified provider."""
    key = api_key.strip() if api_key else ""
    
    if provider == "semanticscholar" or key.startswith("s2k-") or (provider == "auto" and (key.startswith("s2k-") or not key)):
        return await search_papers_semanticscholar(query, key, limit)
    else:
        return await search_papers_serpapi(query, key, limit)
