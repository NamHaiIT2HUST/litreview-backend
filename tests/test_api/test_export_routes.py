from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.export_routes import router as export_router

app = FastAPI()
app.include_router(export_router, prefix="/api/v1")

client = TestClient(app)


def test_export_endpoint_bibtex():
    payload = {
        "format": "bibtex",
        "scope": "keep_only",
        "custom_papers": [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "title": "Deep Learning Survey",
                "authors": ["Ian Goodfellow", "Yoshua Bengio"],
                "year": 2016,
                "journal": "MIT Press",
                "doi": "10.1000/dl",
                "scopus_status": "indexed",
                "screening_decision": "keep"
            }
        ]
    }
    response = client.post("/api/v1/projects/00000000-0000-0000-0000-000000000000/export", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["format"] == "BIBTEX"
    assert data["filename"].endswith(".bib")
    assert "@article{" in data["content"]
    assert "Goodfellow2016Deep" in data["content"]


def test_export_endpoint_csv():
    payload = {
        "format": "csv",
        "scope": "all",
        "include_abstract": True,
        "custom_papers": [
            {
                "id": "22222222-2222-2222-2222-222222222222",
                "title": "NLP Transformers",
                "authors": ["Vaswani et al."],
                "year": 2017,
                "journal": "NeurIPS",
                "doi": "10.1000/tf",
                "abstract": "Attention is all you need."
            }
        ]
    }
    response = client.post("/api/v1/projects/00000000-0000-0000-0000-000000000000/export", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["format"] == "CSV"
    assert data["filename"].endswith(".csv")
    assert "NLP Transformers" in data["content"]


def test_export_endpoint_markdown():
    payload = {
        "format": "markdown",
        "scope": "keep_only",
        "draft_text": "Synthesized literature summary.",
        "custom_papers": [
            {
                "id": "33333333-3333-3333-3333-333333333333",
                "title": "Quantum Computing",
                "authors": ["Richard Feynman"],
                "year": 1982,
                "journal": "Int J Theor Phys"
            }
        ]
    }
    response = client.post("/api/v1/projects/00000000-0000-0000-0000-000000000000/export", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["format"] == "MARKDOWN"
    assert data["filename"].endswith(".md")
    assert "Synthesized literature summary." in data["content"]


def test_export_endpoint_history():
    response = client.get("/api/v1/projects/00000000-0000-0000-0000-000000000000/export/history")
    assert response.status_code == 200
    records = response.json()
    assert isinstance(records, list)
    assert len(records) > 0
