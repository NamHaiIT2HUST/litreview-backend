"""FastAPI router for Module M6 — Export."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.db_models import Paper, Project
from src.services.export_service import (
    generate_bibtex,
    generate_csv,
    generate_json_package,
    generate_markdown_report,
)

router = APIRouter()

# In-memory export history log for active session tracking
EXPORT_HISTORY_LOGS: List[dict] = []


class ExportRequest(BaseModel):
    format: str = Field("bibtex", description="Export format: bibtex, csv, markdown, json")
    scope: str = Field("keep_only", description="Data scope: keep_only, all, synthesis")
    include_abstract: bool = Field(True, description="Whether to include abstract field")
    citation_key_style: str = Field("author_year", description="BibTeX citation key style")
    draft_text: Optional[str] = Field(None, description="Custom synthesis draft text")
    custom_papers: Optional[List[dict]] = Field(None, description="Client-side papers override if DB is empty")


class ExportResponse(BaseModel):
    format: str
    filename: str
    content: str
    papers_count: int
    exported_at: str
    download_url: Optional[str] = None


class ExportHistoryRecord(BaseModel):
    id: str
    project_id: str
    format: str
    filename: str
    papers_count: int
    exported_at: str


@router.post("/projects/{project_id}/export", response_model=ExportResponse)
async def export_project_data(
    project_id: UUID,
    req: ExportRequest,
    db: AsyncSession = Depends(get_db)
):
    """Module 6 — Export data in BibTeX, CSV, Markdown, or JSON format."""
    # 1. Fetch Project with fallback
    project_dict = {
        "id": str(project_id),
        "name": "Literature Review Project",
        "research_question": "Literature Review",
        "research_field": "General",
        "criteria_include": "N/A",
        "criteria_exclude": "N/A",
    }

    try:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if project:
            project_dict = {
                "id": str(project.id),
                "name": project.name,
                "research_question": project.research_question or "",
                "research_field": project.research_field or "",
                "criteria_include": project.criteria_include or "",
                "criteria_exclude": project.criteria_exclude or "",
            }
    except Exception:
        pass

    # 2. Fetch Papers
    papers_list = []
    if req.custom_papers:
        papers_list = req.custom_papers
    else:
        try:
            stmt = select(Paper).where(Paper.project_id == project_id)
            if req.scope == "keep_only":
                stmt = stmt.where(Paper.screening_decision == "keep")
            
            db_result = await db.execute(stmt)
            db_papers = db_result.scalars().all()
            
            if not db_papers and req.scope == "keep_only":
                fallback_stmt = select(Paper).where(Paper.project_id == project_id)
                fallback_res = await db.execute(fallback_stmt)
                db_papers = fallback_res.scalars().all()

            for p in db_papers:
                papers_list.append({
                    "id": str(p.id),
                    "title": p.title,
                    "authors": p.authors if isinstance(p.authors, list) else (p.authors.split(",") if p.authors else []),
                    "year": p.year,
                    "journal": p.journal,
                    "abstract": p.abstract,
                    "doi": p.doi,
                    "issn": p.issn,
                    "url": p.url if hasattr(p, "url") else "#",
                    "citations": p.citations if hasattr(p, "citations") else 0,
                    "scopus_status": p.scopus_status if hasattr(p, "scopus_status") else "undetermined",
                    "screening_decision": p.screening_decision if hasattr(p, "screening_decision") else "keep",
                })
        except Exception:
            papers_list = []

    # Clean non-alphanumeric chars from project name for filename
    clean_proj_name = "".join(c if c.isalnum() else "_" for c in project_dict["name"]).strip("_") or "Project"
    now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    format_clean = req.format.lower().strip()
    
    if format_clean == "bibtex":
        content = generate_bibtex(papers_list, citation_key_style=req.citation_key_style)
        ext = "bib"
    elif format_clean == "csv":
        content = generate_csv(papers_list, include_abstract=req.include_abstract)
        ext = "csv"
    elif format_clean == "markdown" or format_clean == "md":
        content = generate_markdown_report(
            project=project_dict,
            papers=papers_list,
            draft_text=req.draft_text,
            include_abstract=req.include_abstract
        )
        ext = "md"
    elif format_clean == "json":
        content = generate_json_package(
            project=project_dict,
            papers=papers_list,
            draft_text=req.draft_text
        )
        ext = "json"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format '{req.format}'. Supported: bibtex, csv, markdown, json")

    filename = f"{clean_proj_name}_{format_clean.upper()}_{now_str}.{ext}"
    exported_at = datetime.now(timezone.utc).isoformat()

    # Log to export session history
    history_record = {
        "id": f"exp_{now_str}",
        "project_id": str(project_id),
        "format": format_clean.upper(),
        "filename": filename,
        "papers_count": len(papers_list),
        "exported_at": exported_at,
        "content": content,
    }
    EXPORT_HISTORY_LOGS.insert(0, history_record)

    return ExportResponse(
        format=format_clean.upper(),
        filename=filename,
        content=content,
        papers_count=len(papers_list),
        exported_at=exported_at
    )


@router.get("/projects/{project_id}/export/history", response_model=List[ExportHistoryRecord])
async def get_export_history(project_id: UUID):
    """Get recent export history for a project."""
    p_id_str = str(project_id)
    records = [
        ExportHistoryRecord(
            id=item["id"],
            project_id=item["project_id"],
            format=item["format"],
            filename=item["filename"],
            papers_count=item["papers_count"],
            exported_at=item["exported_at"]
        )
        for item in EXPORT_HISTORY_LOGS
        if item["project_id"] == p_id_str
    ]
    return records
