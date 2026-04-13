"""Tests for harvest/offers.py, scorecards.py, interviews.py."""
from __future__ import annotations

import httpx
import pytest
import respx

from greenhouse_mcp.client import GreenhouseClient

HARVEST_BASE = "https://harvest.greenhouse.io/v1"


@pytest.fixture
def client() -> GreenhouseClient:
    return GreenhouseClient(api_key="test")


# --- offers ---

@respx.mock
async def test_list_offers(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.offers import list_offers

    respx.get(f"{HARVEST_BASE}/offers").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "status": "sent"}])
    )
    result = await list_offers(client)
    assert result["items"][0]["status"] == "sent"


@respx.mock
async def test_list_offers_for_application(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.offers import list_offers_for_application

    respx.get(f"{HARVEST_BASE}/applications/10/offers").mock(
        return_value=httpx.Response(200, json=[{"id": 2}])
    )
    result = await list_offers_for_application(client, application_id=10)
    assert result["items"] == [{"id": 2}]


@respx.mock
async def test_get_offer(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.offers import get_offer

    respx.get(f"{HARVEST_BASE}/offers/1").mock(
        return_value=httpx.Response(200, json={"id": 1, "status": "accepted"})
    )
    result = await get_offer(client, offer_id=1)
    assert result["id"] == 1


@respx.mock
async def test_get_current_offer(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.offers import get_current_offer

    respx.get(f"{HARVEST_BASE}/applications/10/offers/current_offer").mock(
        return_value=httpx.Response(200, json={"id": 3, "status": "sent"})
    )
    result = await get_current_offer(client, application_id=10)
    assert result["status"] == "sent"


@respx.mock
async def test_update_current_offer(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.offers import update_current_offer

    respx.patch(f"{HARVEST_BASE}/applications/10/offers/current_offer").mock(
        return_value=httpx.Response(200, json={"id": 3, "starts_at": "2026-01-01"})
    )
    result = await update_current_offer(client, application_id=10, starts_at="2026-01-01")
    assert result["starts_at"] == "2026-01-01"


# --- scorecards ---

@respx.mock
async def test_list_scorecards(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.scorecards import list_scorecards

    respx.get(f"{HARVEST_BASE}/scorecards").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "overall_recommendation": "yes"}])
    )
    result = await list_scorecards(client)
    assert result["items"][0]["overall_recommendation"] == "yes"


@respx.mock
async def test_list_scorecards_for_application(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.scorecards import list_scorecards_for_application

    respx.get(f"{HARVEST_BASE}/applications/10/scorecards").mock(
        return_value=httpx.Response(200, json=[{"id": 2}])
    )
    result = await list_scorecards_for_application(client, application_id=10)
    assert result["items"] == [{"id": 2}]


@respx.mock
async def test_get_scorecard(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.scorecards import get_scorecard

    respx.get(f"{HARVEST_BASE}/scorecards/5").mock(
        return_value=httpx.Response(200, json={"id": 5, "overall_recommendation": "no"})
    )
    result = await get_scorecard(client, scorecard_id=5)
    assert result["id"] == 5


# --- interviews ---

@respx.mock
async def test_list_interviews(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.interviews import list_interviews

    respx.get(f"{HARVEST_BASE}/scheduled_interviews").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "status": "scheduled"}])
    )
    result = await list_interviews(client)
    assert result["items"][0]["status"] == "scheduled"


@respx.mock
async def test_list_interviews_for_application(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.interviews import list_interviews_for_application

    respx.get(f"{HARVEST_BASE}/applications/10/scheduled_interviews").mock(
        return_value=httpx.Response(200, json=[{"id": 2}])
    )
    result = await list_interviews_for_application(client, application_id=10)
    assert result["items"] == [{"id": 2}]


@respx.mock
async def test_get_interview(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.interviews import get_interview

    respx.get(f"{HARVEST_BASE}/scheduled_interviews/1").mock(
        return_value=httpx.Response(200, json={"id": 1, "status": "complete"})
    )
    result = await get_interview(client, interview_id=1)
    assert result["id"] == 1


@respx.mock
async def test_create_interview(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.interviews import create_interview

    respx.post(f"{HARVEST_BASE}/applications/10/scheduled_interviews").mock(
        return_value=httpx.Response(201, json={"id": 9, "status": "scheduled"})
    )
    result = await create_interview(
        client,
        application_id=10,
        interview_id=3,
        interviewer_ids=[100, 101],
        start="2026-05-01T10:00:00Z",
        end="2026-05-01T11:00:00Z",
    )
    assert result["id"] == 9


@respx.mock
async def test_update_interview(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.interviews import update_interview

    respx.patch(f"{HARVEST_BASE}/scheduled_interviews/1").mock(
        return_value=httpx.Response(200, json={"id": 1, "start": "2026-05-02T10:00:00Z"})
    )
    result = await update_interview(client, interview_id=1, start="2026-05-02T10:00:00Z")
    assert result["start"] == "2026-05-02T10:00:00Z"


@respx.mock
async def test_delete_interview(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.interviews import delete_interview

    respx.delete(f"{HARVEST_BASE}/scheduled_interviews/1").mock(
        return_value=httpx.Response(200, json={"message": "deleted"})
    )
    result = await delete_interview(client, interview_id=1)
    assert result["message"] == "deleted"
