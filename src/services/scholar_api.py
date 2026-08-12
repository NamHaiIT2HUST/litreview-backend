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


def extract_issn_from_openalex_location(location: Optional[dict]) -> Optional[str]:
    """
    Lấy ISSN từ 1 OpenAlex location object (primary_location hoặc best_oa_location).
    Ưu tiên issn_l (linking ISSN, ổn định nhất) -> fallback issn[0] (list print/electronic).
    Trả None nếu không có — KHÔNG suy diễn/bịa ISSN.
    """
    if not location or not isinstance(location, dict):
        return None
    source = location.get("source") or {}
    if not isinstance(source, dict):
        return None
    issn_l = source.get("issn_l")
    if issn_l and isinstance(issn_l, str):
        return issn_l
    issn_list = source.get("issn")
    if isinstance(issn_list, list) and issn_list:
        return issn_list[0]
    return None


async def fetch_full_abstract_openalex(client: httpx.AsyncClient, title: str) -> tuple[Optional[str], str, Optional[str], Optional[str]]:
    """
    Tự động tra cứu OpenAlex (miễn phí, 250M+ bài báo) để lấy Full Abstract nguyên bản,
    DOI, ISSN và Tên Tạp chí (cần cho Module 4 Quality Check).
    Trả về (abstract, doi, issn, journal).
    """
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
                primary_loc = item.get("primary_location") or {}
                issn = extract_issn_from_openalex_location(primary_loc)
                source_obj = primary_loc.get("source") or {} if isinstance(primary_loc, dict) else {}
                journal = source_obj.get("display_name") if isinstance(source_obj, dict) else None
                return (full_abstract if len(full_abstract) > 50 else None), doi, issn, journal
    except Exception:
        pass
    return None, "N/A", None, None


async def fetch_full_abstract_s2(client: httpx.AsyncClient, title: str) -> tuple[Optional[str], Optional[str], str, Optional[str], Optional[str]]:
    """
    Tra cứu phụ từ Semantic Scholar để bổ sung TL;DR, ISSN và Tên Tạp chí nếu có.
    Trả về (abstract, tldr, doi, issn, journal).
    """
    try:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": title,
            "limit": 1,
            "fields": "title,abstract,tldr,externalIds,publicationVenue"
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
                venue = item.get("publicationVenue") or {}
                issn = venue.get("issn") if isinstance(venue, dict) else None
                journal = venue.get("name") if isinstance(venue, dict) else None
                return abstract, tldr_text, doi, issn, journal
    except Exception:
        pass
    return None, None, "N/A", None, None


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

        year = res.get("publication_year") or datetime.datetime.now().year
        inv_abstract = res.get("abstract_inverted_index")
        abstract = reconstruct_abstract_from_openalex(inv_abstract) or "No abstract provided."
        citations = res.get("cited_by_count") or 0

        primary_loc = res.get("primary_location") or {}
        landing_url = primary_loc.get("landing_page_url") or primary_loc.get("pdf_url") or "#"
        issn = extract_issn_from_openalex_location(primary_loc)

        raw_doi = res.get("doi")
        doi = raw_doi.replace("https://doi.org/", "") if (raw_doi and isinstance(raw_doi, str)) else "N/A"

        paper_id = hashlib.md5(title.encode()).hexdigest()[:10]

        paper = Paper(
            id=f"OA_{paper_id}",
            title=title,
            authors=author_names,
            year=int(year),
            abstract=abstract,
            journal="OpenAlex Scholar",
            doi=doi,
            issn=issn,
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
        "fields": "paperId,title,authors,year,abstract,tldr,citationCount,openAccessPdf,externalIds,publicationVenue"
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

        venue = res.get("publicationVenue") or {}
        issn = venue.get("issn") if isinstance(venue, dict) else None
        journal_name = (venue.get("name") if isinstance(venue, dict) else None) or "Semantic Scholar"

        paper = Paper(
            id=f"S2_{paper_id[:10]}",
            title=title,
            authors=author_names,
            year=int(year),
            abstract=abstract,
            journal=journal_name,
            doi=doi,
            issn=issn,
            url=str(url_link),
            citations=int(citations),
            litScore=calculate_litscore(int(citations), int(year)),
            tldr=tldr_str
        )
        papers.append(paper)

    return papers


async def fetch_crossref_info(client: httpx.AsyncClient, title: str) -> tuple[str, Optional[str], Optional[str]]:
    """
    Tra cứu CrossRef API (miễn phí, không giới hạn rate limit) để lấy DOI, ISSN, và Tên Tạp chí chính xác.
    Trả về (doi, issn, journal).
    """
    try:
        clean_title = re.sub(r':\s*[\w\s\.,]+et\s+al\.?$', '', title, flags=re.IGNORECASE).strip()
        clean_title = re.sub(r'\.\.\.$', '', clean_title).strip()
        url = "https://api.crossref.org/works"
        params = {"query.title": clean_title, "rows": 1}
        headers = {"User-Agent": "LitReviewAgent/1.0 (mailto:admin@litreview.org)"}
        res = await client.get(url, params=params, headers=headers, timeout=4.0)
        if res.status_code == 200:
            items = res.json().get("message", {}).get("items", [])
            if items:
                item = items[0]
                doi = item.get("DOI") or "N/A"
                container = item.get("container-title") or []
                journal = container[0] if (isinstance(container, list) and container) else None
                issn_list = item.get("ISSN") or []
                issn = issn_list[0] if (isinstance(issn_list, list) and issn_list) else None
                return doi, issn, journal
    except Exception:
        pass
    return "N/A", None, None


async def search_papers_serpapi(query: str, api_key: str, limit: int = 10) -> list[Paper]:
    """Search for papers using SerpApi (Google Scholar) and enrich with Full Abstract/ISSN from CrossRef, OpenAlex & Semantic Scholar."""
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

        cr_tasks = [fetch_crossref_info(client, res.get("title", "")) for res in results]
        oa_tasks = [fetch_full_abstract_openalex(client, res.get("title", "")) for res in results]
        s2_tasks = [fetch_full_abstract_s2(client, res.get("title", "")) for res in results]

        cr_results, oa_results, s2_results = await asyncio.gather(
            asyncio.gather(*cr_tasks, return_exceptions=True),
            asyncio.gather(*oa_tasks, return_exceptions=True),
            asyncio.gather(*s2_tasks, return_exceptions=True)
        )

    papers = []

    for idx, res in enumerate(results):
        title = res.get("title") or "Unknown Title"
        pub_info = res.get("publication_info", {})
        summary = pub_info.get("summary", "") if isinstance(pub_info, dict) else ""

        authors = summary.split("-")[0].strip() if "-" in summary else "Unknown Authors"
        author_names = [a.strip() for a in authors.split(",")] if authors and authors != "Unknown Authors" else []
        year_match = re.search(r'\b(19|20)\d{2}\b', summary)
        year = int(year_match.group()) if year_match else datetime.datetime.now().year

        snippet_abstract = res.get("snippet") or "No abstract available."
        url_link = res.get("link") or "#"

        inline_links = res.get("inline_links", {}) if isinstance(res.get("inline_links"), dict) else {}
        cited_by = inline_links.get("cited_by", {}) if isinstance(inline_links, dict) else {}
        citations = cited_by.get("total", 0) if isinstance(cited_by, dict) else 0

        paper_id = hashlib.md5(title.encode()).hexdigest()[:10]

        cr_doi, cr_issn, cr_journal = "N/A", None, None
        if idx < len(cr_results) and not isinstance(cr_results[idx], Exception):
            cr_doi, cr_issn, cr_journal = cr_results[idx]

        oa_abstract, oa_doi, oa_issn, oa_journal = None, "N/A", None, None
        if idx < len(oa_results) and not isinstance(oa_results[idx], Exception):
            oa_abstract, oa_doi, oa_issn, oa_journal = oa_results[idx]

        s2_abstract, tldr_text, s2_doi, s2_issn, s2_journal = None, None, "N/A", None, None
        if idx < len(s2_results) and not isinstance(s2_results[idx], Exception):
            s2_abstract, tldr_text, s2_doi, s2_issn, s2_journal = s2_results[idx]

        final_abstract = snippet_abstract
        if oa_abstract and len(oa_abstract) > len(final_abstract):
            final_abstract = oa_abstract
        if s2_abstract and len(s2_abstract) > len(final_abstract):
            final_abstract = s2_abstract

        final_doi = cr_doi if cr_doi != "N/A" else (s2_doi if s2_doi != "N/A" else oa_doi)
        final_issn = cr_issn or s2_issn or oa_issn

        # Trích xuất Tên Tạp chí từ Google Scholar summary (Ví dụ: "A Author, B Author - Journal Name, 2021 - Publisher")
        extracted_journal = None
        if "-" in summary:
            parts = summary.split("-")
            if len(parts) >= 2:
                candidate = parts[1].strip()
                candidate = re.sub(r',\s*\b(19|20)\d{2}\b.*$', '', candidate).strip()
                if candidate and candidate.lower() not in ("google scholar", "unknown"):
                    extracted_journal = candidate

        final_journal = cr_journal or extracted_journal or s2_journal or oa_journal or "Google Scholar"

        paper = Paper(
            id=f"GS_{paper_id}",
            title=title,
            authors=author_names,
            year=year,
            abstract=final_abstract,
            journal=final_journal,
            doi=final_doi if (final_doi and isinstance(final_doi, str)) else "N/A",
            issn=final_issn,
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
