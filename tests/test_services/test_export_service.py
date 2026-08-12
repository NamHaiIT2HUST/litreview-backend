"""Unit tests for backend export_service.py."""
import json
import pytest
from src.services.export_service import (
    escape_bibtex,
    generate_citation_key,
    generate_bibtex,
    generate_csv,
    generate_markdown_report,
    generate_json_package,
)


def test_escape_bibtex():
    assert escape_bibtex("R&D % test $ # _ { }") == "R\\&D \\% test \\$ \\# \\_ \\{ \\}"
    assert escape_bibtex(None) == ""


def test_generate_citation_key():
    key1 = generate_citation_key(["John Smith", "Alice Jones"], 2024, "Deep Learning for Natural Language")
    assert key1 == "Smith2024Deep"

    existing = {key1}
    key2 = generate_citation_key(["John Smith"], 2024, "Deep Learning for Natural Language", existing)
    assert key2 == "Smith2024Deep_1"


def test_generate_bibtex():
    papers = [
        {
            "id": "123",
            "title": "Machine Learning Advances & Systems",
            "authors": ["Alice Smith", "Bob Jones"],
            "year": 2023,
            "journal": "IEEE Transactions",
            "doi": "10.1109/test.2023",
            "abstract": "This paper presents novel ML algorithms."
        }
    ]
    bib_str = generate_bibtex(papers)
    assert "@article{Smith2023Machine," in bib_str
    assert "title = {Machine Learning Advances \\& Systems}" in bib_str
    assert "author = {Alice Smith and Bob Jones}" in bib_str
    assert "doi = {10.1109/test.2023}" in bib_str


def test_generate_csv():
    papers = [
        {
            "id": "123",
            "title": "Sample Paper Title",
            "authors": ["Alice Smith"],
            "year": 2022,
            "journal": "Nature",
            "doi": "10.1038/sample",
            "issn": "1234-5678",
            "scopus_status": "indexed",
            "screening_decision": "keep",
            "citations": 15,
            "url": "https://example.com",
            "abstract": "Abstract text here."
        }
    ]
    csv_str = generate_csv(papers, include_abstract=True)
    assert csv_str.startswith("\ufeff")  # UTF-8 BOM
    assert "Sample Paper Title" in csv_str
    assert "Alice Smith" in csv_str
    assert "indexed" in csv_str


def test_generate_markdown_report():
    project = {
        "id": "proj-1",
        "name": "AI Review Project",
        "research_question": "What is AI?",
        "research_field": "Computer Science",
        "criteria_include": "2020-2026 papers",
        "criteria_exclude": "Blogs"
    }
    papers = [
        {
            "id": "p1",
            "title": "AI Foundations",
            "authors": ["John Doe"],
            "year": 2024,
            "journal": "AI Journal",
            "doi": "10.1000/ai",
            "scopus_status": "indexed",
            "screening_decision": "keep",
            "abstract": "AI basics."
        }
    ]
    md_str = generate_markdown_report(project, papers, draft_text="Custom synthesis draft here.")
    assert "# AI Review Project" in md_str
    assert "Custom synthesis draft here." in md_str
    assert "[1] **AI Foundations** (2024)" in md_str


def test_generate_json_package():
    project = {"id": "p1", "name": "JSON Proj"}
    papers = [{"id": "paper1", "title": "Paper One"}]
    json_str = generate_json_package(project, papers, draft_text="Draft text")
    data = json.loads(json_str)
    assert data["app"] == "T165 LitReview Agent"
    assert data["papers_count"] == 1
    assert data["papers"][0]["title"] == "Paper One"
