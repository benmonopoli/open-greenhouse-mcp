"""Tests for ingestion/ modules."""
from __future__ import annotations

import httpx
import pytest
import respx

from greenhouse_mcp.client import GreenhouseClient

INGESTION_BASE = "https://api.greenhouse.io/v1/partner"


@pytest.fixture
def client() -> GreenhouseClient:
    return GreenhouseClient(api_key="test", on_behalf_of="user@co.com")


@respx.mock
async def test_post_candidate(client: GreenhouseClient) -> None:
    from greenhouse_mcp.ingestion.candidates import post_candidate

    respx.post(f"{INGESTION_BASE}/candidates").mock(
        return_value=httpx.Response(200, json={"id": 1, "status": "success"})
    )
    result = await post_candidate(
        client, first_name="Ada", last_name="Lovelace", email="ada@example.com"
    )
    assert result["status"] == "success"


@respx.mock
async def test_retrieve_jobs(client: GreenhouseClient) -> None:
    from greenhouse_mcp.ingestion.jobs import retrieve_ingestion_jobs

    respx.get(f"{INGESTION_BASE}/jobs").mock(
        return_value=httpx.Response(200, json=[{"id": 1}])
    )
    result = await retrieve_ingestion_jobs(client)
    assert isinstance(result, (dict, list))


@respx.mock
async def test_retrieve_prospect_pools(client: GreenhouseClient) -> None:
    from greenhouse_mcp.ingestion.prospects import retrieve_prospect_pools

    respx.get(f"{INGESTION_BASE}/prospect_pools").mock(
        return_value=httpx.Response(200, json=[{"id": 1}])
    )
    result = await retrieve_prospect_pools(client)
    assert isinstance(result, (dict, list))


@respx.mock
async def test_retrieve_current_user(client: GreenhouseClient) -> None:
    from greenhouse_mcp.ingestion.users import retrieve_current_user

    respx.get(f"{INGESTION_BASE}/current_user").mock(
        return_value=httpx.Response(200, json={"id": 1, "email": "user@co.com"})
    )
    result = await retrieve_current_user(client)
    assert result["email"] == "user@co.com"


@respx.mock
async def test_post_tracking_link(client: GreenhouseClient) -> None:
    from greenhouse_mcp.ingestion.tracking import post_tracking_link

    respx.post(f"{INGESTION_BASE}/tracking_links").mock(
        return_value=httpx.Response(200, json={"url": "https://example.com/track"})
    )
    result = await post_tracking_link(client, job_id=1, source="LinkedIn")
    assert "url" in result


@respx.mock
async def test_retrieve_candidates(client: GreenhouseClient) -> None:
    from greenhouse_mcp.ingestion.retrieve import retrieve_ingestion_candidates

    respx.get(f"{INGESTION_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=[{"id": 1}])
    )
    result = await retrieve_ingestion_candidates(client)
    assert isinstance(result, (dict, list))
