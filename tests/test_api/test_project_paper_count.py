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


async def _seed_papers(project_id: str, count: int) -> None:
    async with AsyncSessionLocal() as session:
        query = SearchQuery(project_id=uuid.UUID(project_id), query_string="test query")
        session.add(query)
        await session.flush()
        for i in range(count):
            session.add(Paper(
                project_id=uuid.UUID(project_id),
                search_query_id=query.id,
                title=f"Paper {i}",
                authors=[],
                year=2024,
                dedup_key=f"paper-{uuid.uuid4().hex}",
            ))
        await session.commit()


async def _register_and_create_project(client, name="Paper count regression") -> tuple[str, dict]:
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
            "name": name,
            "research_question": "Does the dashboard show the real source count?",
            "research_field": "Software Engineering",
        },
        headers=headers,
    )
    assert create_res.status_code == 201, create_res.text
    return create_res.json()["id"], headers


@pytest.mark.asyncio
async def test_projects_list_reports_real_paper_count_above_fifteen(client):
    project_id, headers = await _register_and_create_project(client)

    # 16 papers: one past the old (bogus) "<= 15" cap that made real projects
    # with a normal-sized literature review display 0 sources instead of the
    # real count.
    await _seed_papers(project_id, 16)

    list_res = await client.get("/api/v1/projects", headers=headers)
    assert list_res.status_code == 200
    projects = list_res.json()
    match = next(p for p in projects if p["id"] == project_id)
    assert match["paper_count"] == 16


@pytest.mark.asyncio
async def test_get_single_project_reports_real_paper_count(client):
    # GET /projects/{id} and list_projects hit the same ProjectResponse shape
    # but were computed by separate code paths -- easy for one to be fixed
    # and the other left returning the field's bare default of 0.
    project_id, headers = await _register_and_create_project(client, name="Single-fetch project")
    await _seed_papers(project_id, 3)

    get_res = await client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["paper_count"] == 3


@pytest.mark.asyncio
async def test_updating_a_project_preserves_its_real_paper_count(client):
    project_id, headers = await _register_and_create_project(client, name="Project to rename")
    await _seed_papers(project_id, 5)

    put_res = await client.put(
        f"/api/v1/projects/{project_id}",
        json={
            "name": "Renamed project",
            "research_question": "Still the same question",
            "research_field": "Software Engineering",
        },
        headers=headers,
    )
    assert put_res.status_code == 200, put_res.text
    assert put_res.json()["paper_count"] == 5


@pytest.mark.asyncio
async def test_projects_list_reports_zero_for_a_project_with_no_papers(client):
    project_id, headers = await _register_and_create_project(client, name="Empty project")

    list_res = await client.get("/api/v1/projects", headers=headers)
    projects = list_res.json()
    match = next(p for p in projects if p["id"] == project_id)
    assert match["paper_count"] == 0
