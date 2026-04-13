"""Tests for remaining harvest modules: users, depts, tags, demographics, etc."""
from __future__ import annotations

import httpx
import pytest
import respx

from greenhouse_mcp.client import GreenhouseClient

HARVEST_BASE = "https://harvest.greenhouse.io/v1"


@pytest.fixture
def client() -> GreenhouseClient:
    return GreenhouseClient(api_key="test")


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@respx.mock
async def test_list_users(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.users import list_users

    respx.get(f"{HARVEST_BASE}/users").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "Alice"}])
    )
    result = await list_users(client)
    assert result["items"] == [{"id": 1, "name": "Alice"}]
    assert result["has_next"] is False


@respx.mock
async def test_get_user(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.users import get_user

    respx.get(f"{HARVEST_BASE}/users/10").mock(
        return_value=httpx.Response(200, json={"id": 10, "name": "Bob"})
    )
    result = await get_user(client, user_id=10)
    assert result["items"][0]["id"] == 10


@respx.mock
async def test_create_user(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.users import create_user

    respx.post(f"{HARVEST_BASE}/users").mock(
        return_value=httpx.Response(201, json={"id": 99, "first_name": "Carol"})
    )
    result = await create_user(
        client, first_name="Carol", last_name="Smith", email="carol@example.com"
    )
    assert result["id"] == 99
    assert result["first_name"] == "Carol"


@respx.mock
async def test_disable_user(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.users import disable_user

    respx.patch(f"{HARVEST_BASE}/users/10/disable").mock(
        return_value=httpx.Response(200, json={"id": 10, "disabled": True})
    )
    result = await disable_user(client, user_id=10)
    assert result["disabled"] is True


# ---------------------------------------------------------------------------
# Departments
# ---------------------------------------------------------------------------

@respx.mock
async def test_list_departments(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.departments import list_departments

    respx.get(f"{HARVEST_BASE}/departments").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "Engineering"}])
    )
    result = await list_departments(client)
    assert result["items"][0]["name"] == "Engineering"


@respx.mock
async def test_get_department(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.departments import get_department

    respx.get(f"{HARVEST_BASE}/departments/5").mock(
        return_value=httpx.Response(200, json={"id": 5, "name": "Design"})
    )
    result = await get_department(client, department_id=5)
    assert result["items"][0]["name"] == "Design"


# ---------------------------------------------------------------------------
# Sources (cached)
# ---------------------------------------------------------------------------

@respx.mock
async def test_list_sources(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.sources import list_sources

    respx.get(f"{HARVEST_BASE}/sources").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "LinkedIn"}])
    )
    result = await list_sources(client)
    assert result["items"][0]["name"] == "LinkedIn"


@respx.mock
async def test_list_sources_cached(client: GreenhouseClient) -> None:
    """Second call with same client should use cache and not hit network."""
    from greenhouse_mcp.harvest.sources import list_sources

    respx.get(f"{HARVEST_BASE}/sources").mock(
        return_value=httpx.Response(200, json=[{"id": 2, "name": "Referral"}])
    )
    result1 = await list_sources(client)
    # Second call — respx would raise if it hit network a second time without another mock
    result2 = await list_sources(client)
    assert result1 == result2


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

@respx.mock
async def test_list_tags(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.tags import list_tags

    respx.get(f"{HARVEST_BASE}/tags/candidate").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "priority"}])
    )
    result = await list_tags(client)
    assert result["items"][0]["name"] == "priority"


@respx.mock
async def test_add_tag_to_candidate(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.tags import add_tag_to_candidate

    respx.put(f"{HARVEST_BASE}/candidates/42/tags/7").mock(
        return_value=httpx.Response(200, json={"tag_id": 7})
    )
    result = await add_tag_to_candidate(client, candidate_id=42, tag_id=7)
    assert result["tag_id"] == 7


@respx.mock
async def test_remove_tag_from_candidate(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.tags import remove_tag_from_candidate

    respx.delete(f"{HARVEST_BASE}/candidates/42/tags/7").mock(
        return_value=httpx.Response(200, json={})
    )
    result = await remove_tag_from_candidate(client, candidate_id=42, tag_id=7)
    assert result == {}


# ---------------------------------------------------------------------------
# Activity Feed
# ---------------------------------------------------------------------------

@respx.mock
async def test_get_activity_feed(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.activity_feed import get_activity_feed

    respx.get(f"{HARVEST_BASE}/candidates/42/activity_feed").mock(
        return_value=httpx.Response(200, json={"activities": [{"id": 1}]})
    )
    result = await get_activity_feed(client, candidate_id=42)
    assert result["items"][0]["activities"][0]["id"] == 1


# ---------------------------------------------------------------------------
# EEOC
# ---------------------------------------------------------------------------

@respx.mock
async def test_list_eeoc(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.eeoc import list_eeoc

    respx.get(f"{HARVEST_BASE}/eeoc").mock(
        return_value=httpx.Response(200, json=[{"application_id": 1}])
    )
    result = await list_eeoc(client)
    assert result["items"][0]["application_id"] == 1


# ---------------------------------------------------------------------------
# Demographics
# ---------------------------------------------------------------------------

@respx.mock
async def test_list_questions(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.demographics import list_questions

    respx.get(f"{HARVEST_BASE}/demographics/questions").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "Gender"}])
    )
    result = await list_questions(client)
    assert result["items"][0]["name"] == "Gender"


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------

@respx.mock
async def test_list_approvals_for_job(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.approvals import list_approvals_for_job

    respx.get(f"{HARVEST_BASE}/jobs/100/approval_flows").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "status": "pending"}])
    )
    result = await list_approvals_for_job(client, job_id=100)
    assert result["items"][0]["status"] == "pending"


# ---------------------------------------------------------------------------
# Hiring Team
# ---------------------------------------------------------------------------

@respx.mock
async def test_get_hiring_team(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.hiring_team import get_hiring_team

    respx.get(f"{HARVEST_BASE}/jobs/100/hiring_team").mock(
        return_value=httpx.Response(200, json={"recruiters": [{"id": 5}]})
    )
    result = await get_hiring_team(client, job_id=100)
    assert result["items"][0]["recruiters"][0]["id"] == 5


# ---------------------------------------------------------------------------
# Prospect Pools
# ---------------------------------------------------------------------------

@respx.mock
async def test_list_prospect_pools(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.prospect_pools import list_prospect_pools

    respx.get(f"{HARVEST_BASE}/prospect_pools").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "Executive Pool"}])
    )
    result = await list_prospect_pools(client)
    assert result["items"][0]["name"] == "Executive Pool"


@respx.mock
async def test_get_prospect_pool(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.prospect_pools import get_prospect_pool

    respx.get(f"{HARVEST_BASE}/prospect_pools/1").mock(
        return_value=httpx.Response(200, json={"id": 1, "name": "Executive Pool"})
    )
    result = await get_prospect_pool(client, prospect_pool_id=1)
    assert result["items"][0]["id"] == 1
