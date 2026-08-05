import asyncio
import datetime
import hashlib
import re
from typing import Optional

import httpx
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


def reconstruct_abstract_from_openalex(inverted_index: dict) -> str:
    """Giải mã chỉ mục ngược (abstract_inverted_index) của OpenAlex thành văn bản Full Abstract hoàn chỉnh."""
    if not inverted_index or not isinstance(inverted_index, dict):
        return ""
    pos_map = {}
    for word, positions in inverted_index.items():
        if isinstance(positions, list):
            for pos in positions:
                pos_map[pos] = word
    sorted_words = [pos_map[i] for i in sorted(pos_map.keys())]
    return " ".join(sorted_words)


async def fetch_full_abstract_openalex(client: httpx.AsyncClient, title: str) -> tuple[Optional[str], str]:
    """Tự động tra cứu OpenAlex (miễn phí, 250M+ bài báo) để lấy Full Abstract nguyên bản và DOI."""
    try:
        url = "https://api.openalex.org/works"
        params = {"search": title, "per-page": 1}
        res = await client.get(url, params=params, timeout=5.0)
        if res.status_code == 200:
            results = res.json().get("results", [])
            if results:
                item = results[0]
                inv = item.get("abstract_inverted_index")
                full_abstract = reconstruct_abstract_from_openalex(inv)
                raw_doi = item.get("doi")
                doi = raw_doi.replace("https://doi.org/", "") if (raw_doi and isinstance(raw_doi, str)) else "N/A"
                return (full_abstract if len(full_abstract) > 50 else None), doi
    except Exception:
        pass
    return None, "N/A"


async def fetch_full_abstract_s2(client: httpx.AsyncClient, title: str) -> tuple[Optional[str], Optional[str], str]:
    """Tra cứu phụ từ Semantic Scholar để bổ sung TL;DR nếu có."""
    try:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": title,
            "limit": 1,
            "fields": "title,abstract,tldr,externalIds"
        }
        res = await client.get(url, params=params, timeout=4.0)
        if res.status_code == 200:
            data = res.json().get("data", [])
            if data:
                item = data[0]
                abstract = item.get("abstract")
                tldr_info = item.get("tldr")
                tldr_text = tldr_info.get("text") if isinstance(tldr_info, dict) else None
                ext_ids = item.get("externalIds") or {}
                raw_doi = ext_ids.get("DOI") if isinstance(ext_ids, dict) else None
                doi = raw_doi if (raw_doi and isinstance(raw_doi, str)) else "N/A"
                return abstract, tldr_text, doi
    except Exception:
        pass
    return None, None, "N/A"


async def search_papers_openalex(query: str, limit: int = 10) -> list[Paper]:
    """Tìm kiếm trực tiếp từ OpenAlex API (Tốc độ cao, không cần API Key, không bao giờ bị 429)."""
    url = "https://api.openalex.org/works"
    params = {"search": query, "per-page": limit}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=12.0)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"OpenAlex API error: {str(e)}")

    results = data.get("results", [])
    papers = []

    for res in results:
        title = res.get("display_name") or res.get("title") or "Unknown Title"
        
        authorships = res.get("authorships") or []
        author_names = []
        for auth in authorships:
            if isinstance(auth, dict):
                author_obj = auth.get("author") or {}
                name = author_obj.get("display_name")
                if name:
                    author_names.append(name)
        authors_str = ", ".join(author_names[:4]) if author_names else "Unknown Authors"
        if len(author_names) > 4:
            authors_str += " et al."

        year = res.get("publication_year") or datetime.datetime.now().year
        inv_abstract = res.get("abstract_inverted_index")
        abstract = reconstruct_abstract_from_openalex(inv_abstract) or "No abstract provided."
        citations = res.get("cited_by_count") or 0

        primary_loc = res.get("primary_location") or {}
        landing_url = primary_loc.get("landing_page_url") or primary_loc.get("pdf_url") or "#"

        raw_doi = res.get("doi")
        doi = raw_doi.replace("https://doi.org/", "") if (raw_doi and isinstance(raw_doi, str)) else "N/A"

        paper_id = hashlib.md5(title.encode()).hexdigest()[:10]

        paper = Paper(
            id=f"OA_{paper_id}",
            title=title,
            authors=authors_str,
            year=int(year),
            abstract=abstract,
            journal="OpenAlex Scholar",
            doi=doi,
            url=str(landing_url),
            citations=int(citations),
            litScore=calculate_litscore(int(citations), int(year)),
            tldr=None
        )
        papers.append(paper)

    return papers


async def search_papers_semanticscholar(query: str, api_key: str = None, limit: int = 10) -> list[Paper]:
    """Search for papers using Semantic Scholar (S2) Graph API. Fallback to OpenAlex if 429 occurs."""
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "paperId,title,authors,year,abstract,tldr,citationCount,openAccessPdf,externalIds"
    }

    headers = {}
    if api_key and api_key.strip():
        headers["x-api-key"] = api_key.strip()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, headers=headers, timeout=12.0)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                return await search_papers_openalex(query, limit)
            elif e.response.status_code in (401, 403):
                raise HTTPException(status_code=401, detail="Invalid Semantic Scholar API Key")
            raise HTTPException(status_code=500, detail=f"Semantic Scholar API error: {str(e)}")
        except Exception:
            return await search_papers_openalex(query, limit)

    results = data.get("data", [])
    papers = []

    for res in results:
        paper_id = str(res.get("paperId", ""))
        title = res.get("title") or "Unknown Title"
        
        raw_authors = res.get("authors", [])
        author_names = [a.get("name", "") for a in raw_authors if isinstance(a, dict) and a.get("name")]
        authors_str = ", ".join(author_names[:4]) if author_names else "Unknown Authors"
        if len(author_names) > 4:
            authors_str += " et al."

        year = res.get("year") or datetime.datetime.now().year
        abstract = res.get("abstract") or "No abstract provided."
        citations = res.get("citationCount") or 0
        
        tldr_obj = res.get("tldr")
        tldr_str = tldr_obj.get("text") if isinstance(tldr_obj, dict) else None

        pdf_info = res.get("openAccessPdf") or {}
        url_link = pdf_info.get("url") if isinstance(pdf_info, dict) else None
        if not url_link:
            url_link = f"https://www.semanticscholar.org/paper/{paper_id}"

        ext_ids = res.get("externalIds") or {}
        raw_doi = ext_ids.get("DOI") if isinstance(ext_ids, dict) else None
        doi = raw_doi if (raw_doi and isinstance(raw_doi, str)) else "N/A"

        paper = Paper(
            id=f"S2_{paper_id[:10]}",
            title=title,
            authors=authors_str,
            year=int(year),
            abstract=abstract,
            journal="Semantic Scholar",
            doi=doi,
            url=str(url_link),
            citations=int(citations),
            litScore=calculate_litscore(int(citations), int(year)),
            tldr=tldr_str
        )
        papers.append(paper)

    return papers


async def search_papers_serpapi(query: str, api_key: str, limit: int = 10) -> list[Paper]:
    """Search for papers using SerpApi (Google Scholar) and enrich with Full Abstract from OpenAlex & Semantic Scholar."""
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
        
        oa_tasks = [fetch_full_abstract_openalex(client, res.get("title", "")) for res in results]
        s2_tasks = [fetch_full_abstract_s2(client, res.get("title", "")) for res in results]
        
        oa_results, s2_results = await asyncio.gather(
            asyncio.gather(*oa_tasks, return_exceptions=True),
            asyncio.gather(*s2_tasks, return_exceptions=True)
        )

    papers = []
    
    for idx, res in enumerate(results):
        title = res.get("title") or "Unknown Title"
        pub_info = res.get("publication_info", {})
        summary = pub_info.get("summary", "") if isinstance(pub_info, dict) else ""
        
        authors = summary.split("-")[0].strip() if "-" in summary else "Unknown Authors"
        year_match = re.search(r'\b(19|20)\d{2}\b', summary)
        year = int(year_match.group()) if year_match else datetime.datetime.now().year
        
        snippet_abstract = res.get("snippet") or "No abstract available."
        journal = "Google Scholar"
        url_link = res.get("link") or "#"
        
        inline_links = res.get("inline_links", {}) if isinstance(res.get("inline_links"), dict) else {}
        cited_by = inline_links.get("cited_by", {}) if isinstance(inline_links, dict) else {}
        citations = cited_by.get("total", 0) if isinstance(cited_by, dict) else 0

        paper_id = hashlib.md5(title.encode()).hexdigest()[:10]
        
        oa_abstract, oa_doi = None, "N/A"
        if idx < len(oa_results) and not isinstance(oa_results[idx], Exception):
            oa_abstract, oa_doi = oa_results[idx]
            
        s2_abstract, tldr_text, s2_doi = None, None, "N/A"
        if idx < len(s2_results) and not isinstance(s2_results[idx], Exception):
            s2_abstract, tldr_text, s2_doi = s2_results[idx]
            
        final_abstract = snippet_abstract
        if oa_abstract and len(oa_abstract) > len(final_abstract):
            final_abstract = oa_abstract
        if s2_abstract and len(s2_abstract) > len(final_abstract):
            final_abstract = s2_abstract
            
        final_doi = s2_doi if s2_doi != "N/A" else oa_doi

        paper = Paper(
            id=f"GS_{paper_id}",
            title=title,
            authors=authors,
            year=year,
            abstract=final_abstract,
            journal=journal,
            doi=final_doi if (final_doi and isinstance(final_doi, str)) else "N/A",
            url=str(url_link),
            citations=int(citations),
            litScore=calculate_litscore(citations, year),
            tldr=tldr_text
        )
        papers.append(paper)

    return papers


async def search_papers_auto(query: str, api_key: str = None, provider: str = "auto", limit: int = 10) -> list[Paper]:
    """Auto-detect provider or use specified provider."""
    key = api_key.strip() if api_key else ""

    if provider == "semanticscholar" or key.startswith("s2k-") or (provider == "auto" and (key.startswith("s2k-") or not key)):
        return await search_papers_semanticscholar(query, key, limit)
    else:
        return await search_papers_serpapi(query, key, limit)