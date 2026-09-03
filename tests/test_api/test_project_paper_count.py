"""Regression test for GET /projects returning a real, device-independent
paper_count.

Before this fix, ProjectResponse never had a paper_count field at all, so the
dashboard card fell back entirely to per-browser localStorage caches to guess
how many papers a project had -- which showed "0 nguồn" on any device/browser
that hadn't locally cached that project (most visibly reported on mobile).
The frontend fallback also silently capped the count at 15, which would have
kept masking real projects even after paper_count started being returned.
"""
import uuid

import pytest

from src.database import AsyncSessionLocal
from src.models.db_models import Paper, SearchQuery


@pytest.mark.asyncio
async def test_projects_list_reports_real_paper_count_above_fifteen(client):
    username = f"papercount_{uuid.uuid4().hex[:10]}"
    register_res = await client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "test-password-123"},
    )
    assert register_res.status_code == 200, register_res.text
    token = register_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_res = await client.post(
        "/api/v1/projects",
        json={
            "name": "Paper count regression",
            "research_question": "Does the dashboard show the real source count?",
            "research_field": "Software Engineering",
        },
        headers=headers,
    )
    assert create_res.status_code == 201, create_res.text
    project_id = create_res.json()["id"]

    # 16 papers: one past the old (bogus) "<= 15" cap that made real projects
    # with a normal-sized literature review display 0 sources instead of the
    # real count.
    async with AsyncSessionLocal() as session:
        query = SearchQuery(project_id=uuid.UUID(project_id), query_string="test query")
        session.add(query)
        await session.flush()
        for i in range(16):
            session.add(Paper(
                project_id=uuid.UUID(project_id),
                search_query_id=query.id,
                title=f"Paper {i}",
                authors=[],
                year=2024,
                dedup_key=f"paper-{uuid.uuid4().hex}",
            ))
        await session.commit()

    list_res = await client.get("/api/v1/projects", headers=headers)
    assert list_res.status_code == 200
    projects = list_res.json()
    match = next(p for p in projects if p["id"] == project_id)
    assert match["paper_count"] == 16


@pytest.mark.asyncio
async def test_projects_list_reports_zero_for_a_project_with_no_papers(client):
    username = f"papercount_{uuid.uuid4().hex[:10]}"
    register_res = await client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "test-password-123"},
    )
    token = register_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_res = await client.post(
        "/api/v1/projects",
        json={
            "name": "Empty project",
            "research_question": "No papers added yet",
            "research_field": "Software Engineering",
        },
        headers=headers,
    )
    project_id = create_res.json()["id"]

    list_res = await client.get("/api/v1/projects", headers=headers)
    projects = list_res.json()
    match = next(p for p in projects if p["id"] == project_id)
    assert match["paper_count"] == 0
