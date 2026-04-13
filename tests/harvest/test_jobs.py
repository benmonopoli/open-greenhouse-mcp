"""Tests for harvest/jobs.py, job_posts.py, job_stages.py, job_openings.py."""
from __future__ import annotations

import httpx
import pytest
import respx

from greenhouse_mcp.client import GreenhouseClient

HARVEST_BASE = "https://harvest.greenhouse.io/v1"


@pytest.fixture
def client() -> GreenhouseClient:
    return GreenhouseClient(api_key="test")


# --- jobs ---

@respx.mock
async def test_list_jobs(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.jobs import list_jobs

    respx.get(f"{HARVEST_BASE}/jobs").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "Engineer"}])
    )
    result = await list_jobs(client)
    assert result["items"] == [{"id": 1, "name": "Engineer"}]
    assert result["has_next"] is False


@respx.mock
async def test_list_jobs_with_filters(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.jobs import list_jobs

    respx.get(f"{HARVEST_BASE}/jobs").mock(
        return_value=httpx.Response(200, json=[{"id": 2}])
    )
    result = await list_jobs(client, status="open", department_id=10)
    assert result["items"] == [{"id": 2}]


@respx.mock
async def test_get_job(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.jobs import get_job

    respx.get(f"{HARVEST_BASE}/jobs/42").mock(
        return_value=httpx.Response(200, json={"id": 42, "name": "Designer"})
    )
    result = await get_job(client, job_id=42)
    assert result["id"] == 42


@respx.mock
async def test_create_job(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.jobs import create_job

    respx.post(f"{HARVEST_BASE}/jobs").mock(
        return_value=httpx.Response(201, json={"id": 99, "name": "PM"})
    )
    result = await create_job(client, template_job_id=5, job_name="PM")
    assert result["id"] == 99


@respx.mock
async def test_update_job(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.jobs import update_job

    respx.patch(f"{HARVEST_BASE}/jobs/42").mock(
        return_value=httpx.Response(200, json={"id": 42, "status": "closed"})
    )
    result = await update_job(client, job_id=42, status="closed")
    assert result["status"] == "closed"


# --- job_posts ---

@respx.mock
async def test_list_job_posts(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_posts import list_job_posts

    respx.get(f"{HARVEST_BASE}/job_posts").mock(
        return_value=httpx.Response(200, json=[{"id": 10, "title": "Senior Dev"}])
    )
    result = await list_job_posts(client)
    assert result["items"][0]["title"] == "Senior Dev"


@respx.mock
async def test_list_job_posts_for_job(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_posts import list_job_posts_for_job

    respx.get(f"{HARVEST_BASE}/jobs/42/job_posts").mock(
        return_value=httpx.Response(200, json=[{"id": 11}])
    )
    result = await list_job_posts_for_job(client, job_id=42)
    assert result["items"] == [{"id": 11}]


@respx.mock
async def test_get_job_post(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_posts import get_job_post

    respx.get(f"{HARVEST_BASE}/job_posts/10").mock(
        return_value=httpx.Response(200, json={"id": 10, "title": "Dev"})
    )
    result = await get_job_post(client, job_post_id=10)
    assert result["id"] == 10


@respx.mock
async def test_update_job_post(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_posts import update_job_post

    respx.patch(f"{HARVEST_BASE}/job_posts/10").mock(
        return_value=httpx.Response(200, json={"id": 10, "title": "Lead Dev"})
    )
    result = await update_job_post(client, job_post_id=10, title="Lead Dev")
    assert result["title"] == "Lead Dev"


@respx.mock
async def test_update_job_post_status(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_posts import update_job_post_status

    respx.patch(f"{HARVEST_BASE}/job_posts/10").mock(
        return_value=httpx.Response(200, json={"id": 10, "status": "live"})
    )
    result = await update_job_post_status(client, job_post_id=10, status="live")
    assert result["status"] == "live"


# --- job_stages ---

@respx.mock
async def test_list_job_stages(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_stages import list_job_stages

    respx.get(f"{HARVEST_BASE}/job_stages").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "Application Review"}])
    )
    result = await list_job_stages(client)
    assert result["items"][0]["name"] == "Application Review"


@respx.mock
async def test_list_job_stages_for_job(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_stages import list_job_stages_for_job

    respx.get(f"{HARVEST_BASE}/jobs/42/stages").mock(
        return_value=httpx.Response(200, json=[{"id": 2, "name": "Phone Screen"}])
    )
    result = await list_job_stages_for_job(client, job_id=42)
    assert result["items"][0]["name"] == "Phone Screen"


@respx.mock
async def test_get_job_stage(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_stages import get_job_stage

    respx.get(f"{HARVEST_BASE}/job_stages/5").mock(
        return_value=httpx.Response(200, json={"id": 5, "name": "Onsite"})
    )
    result = await get_job_stage(client, job_stage_id=5)
    assert result["id"] == 5


# --- job_openings ---

@respx.mock
async def test_list_job_openings(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_openings import list_job_openings

    respx.get(f"{HARVEST_BASE}/jobs/42/openings").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "status": "open"}])
    )
    result = await list_job_openings(client, job_id=42)
    assert result["items"][0]["status"] == "open"


@respx.mock
async def test_get_job_opening(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_openings import get_job_opening

    respx.get(f"{HARVEST_BASE}/jobs/42/openings/1").mock(
        return_value=httpx.Response(200, json={"id": 1, "status": "open"})
    )
    result = await get_job_opening(client, job_id=42, opening_id=1)
    assert result["id"] == 1


@respx.mock
async def test_create_job_opening(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_openings import create_job_opening

    respx.post(f"{HARVEST_BASE}/jobs/42/openings").mock(
        return_value=httpx.Response(201, json={"id": 7, "status": "open"})
    )
    result = await create_job_opening(client, job_id=42, status="open")
    assert result["id"] == 7


@respx.mock
async def test_update_job_opening(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_openings import update_job_opening

    respx.patch(f"{HARVEST_BASE}/jobs/42/openings/1").mock(
        return_value=httpx.Response(200, json={"id": 1, "status": "closed"})
    )
    result = await update_job_opening(client, job_id=42, opening_id=1, status="closed")
    assert result["status"] == "closed"


@respx.mock
async def test_delete_job_opening(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_openings import delete_job_opening

    respx.delete(f"{HARVEST_BASE}/jobs/42/openings/1").mock(
        return_value=httpx.Response(200, json={"message": "deleted"})
    )
    result = await delete_job_opening(client, job_id=42, opening_id=1)
    assert result["message"] == "deleted"
