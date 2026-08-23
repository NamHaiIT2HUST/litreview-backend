import pytest


@pytest.mark.asyncio
async def test_review_endpoint_returns_draft_and_kpi(client):
    response = await client.post("/api/v1/slr-swarm/review", json={"idea": "deep learning cho ECG"})

    assert response.status_code == 200
    body = response.json()
    assert body["error"] == ""
    assert body["papers_found"] >= 2
    assert body["gate_passed"] is True
    assert "\\begin{tabular}" in body["latex"]
    assert body["bibtex"].startswith("@article{")
    assert body["kpi"]["grounding_precision"] >= 0.8
    assert body["cost_saved_usd"] > 0


@pytest.mark.asyncio
async def test_review_endpoint_rejects_empty_idea(client):
    response = await client.post("/api/v1/slr-swarm/review", json={"idea": ""})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_analyze_endpoint_profiles_and_plans(client):
    csv_text = "age,group\n" + "\n".join(f"{20 + i},A" for i in range(35))

    response = await client.post(
        "/api/v1/slr-swarm/analyze", json={"csv_text": csv_text, "goal": "so sánh nhóm"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["rows"] == 35
    assert body["profile"]["numeric_columns"] == ["age"]
    assert "pandas" in body["plan"]["code"]


@pytest.mark.asyncio
async def test_analyze_endpoint_rejects_unreadable_data(client):
    response = await client.post("/api/v1/slr-swarm/analyze", json={"csv_text": "   "})

    assert response.status_code == 422
