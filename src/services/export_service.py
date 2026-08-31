"""Export service for T165 LitReview Agent.

Provides pure Python utilities and formatting logic for exporting literature review data into:
- BibTeX (.bib)
- CSV (.csv)
- Markdown Literature Review Report (.md)
- JSON Data Package (.json)
"""
from __future__ import annotations

import csv
import io
import json
import re
from datetime import UTC, datetime
from typing import Any


def escape_bibtex(text: str | None) -> str:
    """Escapes special LaTeX/BibTeX characters."""
    if not text:
        return ""

    replacements = [
        ('\\', '\\textbackslash{}'),
        ('&', '\\&'),
        ('%', '\\%'),
        ('$', '\\$'),
        ('#', '\\#'),
        ('_', '\\_'),
        ('{', '\\{'),
        ('}', '\\}'),
        ('~', '\\textasciitilde{}'),
        ('^', '\\textasciicircum{}'),
    ]
    result = text
    for old, new in replacements:
        result = result.replace(old, new)
    return result


def generate_citation_key(authors: Any, year: int | None, title: str, existing_keys: set[str] | None = None) -> str:
    """Generates a clean, unique citation key for BibTeX entries.

    Format: AuthorLastnameYearTitleWord (e.g. Smith2024Deep)
    """
    if existing_keys is None:
        existing_keys = set()

    author_str = ""
    if isinstance(authors, list) and len(authors) > 0:
        author_str = str(authors[0])
    elif isinstance(authors, str) and authors.strip():
        author_str = authors.split(',')[0].split(';')[0].split(' and ')[0].strip()

    author_parts = re.findall(r'[A-Za-z]+', author_str)
    author_key = author_parts[-1].capitalize() if author_parts else "Author"
    year_key = str(year) if year else "ND"

    title_words = re.findall(r'[A-Za-z0-9]+', title or "")
    title_key = "Paper"
    for word in title_words:
        if len(word) >= 4 and word.lower() not in {"with", "from", "that", "this", "some", "using", "study", "review"}:
            title_key = word.capitalize()
            break

    base_key = f"{author_key}{year_key}{title_key}"
    key = base_key
    counter = 1
    while key in existing_keys:
        key = f"{base_key}_{counter}"
        counter += 1

    existing_keys.add(key)
    return key


def generate_bibtex(papers: list[dict[str, Any] | Any], citation_key_style: str = "author_year") -> str:
    """Generates BibTeX formatted string for a collection of papers."""
    entries = []
    existing_keys: set[str] = set()

    for paper in papers:
        p_dict = paper if isinstance(paper, dict) else paper.__dict__

        title = p_dict.get("title", "Untitled")
        authors = p_dict.get("authors", [])
        if isinstance(authors, list):
            authors_str = " and ".join(str(a) for a in authors if a)
        else:
            authors_str = str(authors) if authors else "Unknown"

        year = p_dict.get("year")
        journal = p_dict.get("journal") or p_dict.get("publisher", "")
        doi = p_dict.get("doi", "")
        issn = p_dict.get("issn", "")
        url = p_dict.get("url", "")
        abstract = p_dict.get("abstract", "")

        key = generate_citation_key(authors, year, title, existing_keys)

        bib_fields = [
            f"  title = {{{escape_bibtex(title)}}}",
            f"  author = {{{escape_bibtex(authors_str)}}}",
        ]
        if journal:
            bib_fields.append(f"  journal = {{{escape_bibtex(journal)}}}")
        if year:
            bib_fields.append(f"  year = {{{year}}}")
        if doi:
            bib_fields.append(f"  doi = {{{escape_bibtex(doi)}}}")
        if issn:
            bib_fields.append(f"  issn = {{{escape_bibtex(issn)}}}")
        if url and url != "#":
            bib_fields.append(f"  url = {{{escape_bibtex(url)}}}")
        if abstract:
            clean_abstract = " ".join(abstract.split())
            bib_fields.append(f"  abstract = {{{escape_bibtex(clean_abstract)}}}")

        entry_content = ",\n".join(bib_fields)
        entry = f"@article{{{key},\n{entry_content}\n}}"
        entries.append(entry)

    return "\n\n".join(entries)


def generate_csv(papers: list[dict[str, Any] | Any], include_abstract: bool = True) -> str:
    """Generates CSV string with UTF-8 BOM for Excel compatibility."""
    output = io.StringIO()
    output.write('\ufeff')

    fieldnames = [
        "ID",
        "Title",
        "Authors",
        "Year",
        "Journal",
        "DOI",
        "ISSN",
        "Scopus Status",
        "Screening Decision",
        "Citations",
        "URL",
    ]
    if include_abstract:
        fieldnames.append("Abstract")

    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()

    for p in papers:
        p_dict = p if isinstance(p, dict) else p.__dict__
        authors = p_dict.get("authors", [])
        if isinstance(authors, list):
            authors_str = ", ".join(str(a) for a in authors if a)
        else:
            authors_str = str(authors) if authors else ""

        row = {
            "ID": str(p_dict.get("id", "")),
            "Title": p_dict.get("title", ""),
            "Authors": authors_str,
            "Year": p_dict.get("year", "") or "",
            "Journal": p_dict.get("journal", "") or "",
            "DOI": p_dict.get("doi", "") or "",
            "ISSN": p_dict.get("issn", "") or "",
            "Scopus Status": p_dict.get("scopus_status", "undetermined"),
            "Screening Decision": p_dict.get("screening_decision", "maybe"),
            "Citations": p_dict.get("citations", 0),
            "URL": p_dict.get("url", "#"),
        }
        if include_abstract:
            row["Abstract"] = p_dict.get("abstract", "") or ""

        writer.writerow(row)

    return output.getvalue()


def generate_markdown_report(
    project: dict[str, Any] | Any | None,
    papers: list[dict[str, Any] | Any],
    draft_text: str | None = None,
    include_abstract: bool = True
) -> str:
    """Compiles a full Literature Review report in Markdown format."""
    proj_dict = (project if isinstance(project, dict) else project.__dict__) if project else {}

    proj_name = proj_dict.get("name", "Literature Review Project")
    rq = proj_dict.get("research_question", "N/A")
    field = proj_dict.get("research_field", "General")
    criteria_inc = proj_dict.get("criteria_include", "N/A")
    criteria_exc = proj_dict.get("criteria_exclude", "N/A")
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

    md_lines = [
        f"# {proj_name}",
        "",
        f"**Generated Date:** {timestamp}  ",
        f"**Research Field:** {field}  ",
        f"**Research Question:** {rq}  ",
        "",
        "---",
        "",
        "## 1. Executive Summary & Setup",
        "",
        f"- **Inclusion Criteria:** {criteria_inc}",
        f"- **Exclusion Criteria:** {criteria_exc}",
        f"- **Total Reviewed Papers:** {len(papers)}",
        "",
        "### Paper Summary Status",
        "",
        "| # | Title | Authors | Year | Journal | Scopus | Decision |",
        "|---|-------|---------|------|---------|--------|----------|",
    ]

    for idx, p in enumerate(papers, 1):
        p_dict = p if isinstance(p, dict) else p.__dict__
        title = p_dict.get("title", "Untitled").replace("|", "\\|")
        authors = p_dict.get("authors", [])
        if isinstance(authors, list):
            authors_str = ", ".join(str(a) for a in authors[:2])
            if len(authors) > 2:
                authors_str += " et al."
        else:
            authors_str = str(authors)
        authors_str = authors_str.replace("|", "\\|")
        year = p_dict.get("year", "N/A")
        journal = (p_dict.get("journal") or "N/A").replace("|", "\\|")
        scopus = p_dict.get("scopus_status", "undetermined")
        decision = p_dict.get("screening_decision", "keep")

        md_lines.append(f"| {idx} | {title} | {authors_str} | {year} | {journal} | `{scopus}` | **{decision.upper()}** |")

    md_lines.extend([
        "",
        "---",
        "",
        "## 2. Synthesis & Literature Review Draft",
        "",
    ])

    if draft_text and draft_text.strip():
        md_lines.append(draft_text.strip())
    else:
        md_lines.append(
            "_No custom synthesis draft generated yet. Below is the synthesized list of key evidence and paper summaries._"
        )

    md_lines.extend([
        "",
        "---",
        "",
        "## 3. Detailed References & Bibliography",
        "",
    ])

    for idx, p in enumerate(papers, 1):
        p_dict = p if isinstance(p, dict) else p.__dict__
        title = p_dict.get("title", "Untitled")
        authors = p_dict.get("authors", [])
        if isinstance(authors, list):
            authors_str = ", ".join(str(a) for a in authors)
        else:
            authors_str = str(authors)
        year = p_dict.get("year", "N/A")
        journal = p_dict.get("journal", "")
        doi = p_dict.get("doi", "")
        url = p_dict.get("url", "#")
        abstract = p_dict.get("abstract", "")

        ref_entry = f"[{idx}] **{title}** ({year}). *{authors_str}*."
        if journal:
            ref_entry += f" {journal}."
        if doi:
            ref_entry += f" DOI: [{doi}](https://doi.org/{doi})"
        elif url and url != "#":
            ref_entry += f" Link: [{url}]({url})"

        md_lines.append(ref_entry)
        if include_abstract and abstract:
            md_lines.append(f"> **Abstract:** {abstract}")
        md_lines.append("")

    return "\n".join(md_lines)


def generate_json_package(
    project: dict[str, Any] | Any | None,
    papers: list[dict[str, Any] | Any],
    draft_text: str | None = None
) -> str:
    """Generates structured JSON string packaging project data."""
    proj_dict = (project if isinstance(project, dict) else project.__dict__) if project else {}

    clean_papers = []
    for p in papers:
        p_dict = p if isinstance(p, dict) else p.__dict__
        serializable_p = {}
        for k, v in p_dict.items():
            if k.startswith("_"):
                continue
            if isinstance(v, (str, int, float, bool, list, dict, type(None))):
                serializable_p[k] = v
            else:
                serializable_p[k] = str(v)
        clean_papers.append(serializable_p)

    payload = {
        "app": "T165 LitReview Agent",
        "exported_at": datetime.now(UTC).isoformat(),
        "project": {
            "id": str(proj_dict.get("id", "")),
            "name": proj_dict.get("name", "Untitled Project"),
            "research_question": proj_dict.get("research_question", ""),
            "research_field": proj_dict.get("research_field", ""),
            "criteria_include": proj_dict.get("criteria_include", ""),
            "criteria_exclude": proj_dict.get("criteria_exclude", ""),
        },
        "papers_count": len(clean_papers),
        "papers": clean_papers,
        "synthesis_draft": draft_text or "",
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)
