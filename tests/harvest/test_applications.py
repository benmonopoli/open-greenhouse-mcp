"""Tests for harvest/applications.py."""
from __future__ import annotations

import httpx
import pytest
import respx

from greenhouse_mcp.client import GreenhouseClient

HARVEST_BASE = "https://harvest.greenhouse.io/v1"


@pytest.fixture
def client() -> GreenhouseClient:
    return GreenhouseClient(api_key="test")


@respx.mock
async def test_list_applications(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import list_applications

    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "candidate_id": 10}])
    )
    result = await list_applications(client)
    assert result["items"] == [{"id": 1, "candidate_id": 10}]
    assert result["has_next"] is False


@respx.mock
async def test_list_applications_with_filters(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import list_applications

    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=[{"id": 2, "status": "active"}])
    )
    result = await list_applications(client, job_id=5, status="active", candidate_id=10)
    assert result["items"][0]["status"] == "active"


@respx.mock
async def test_get_application(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import get_application

    respx.get(f"{HARVEST_BASE}/applications/100").mock(
        return_value=httpx.Response(200, json={"id": 100, "job_id": 5})
    )
    result = await get_application(client, application_id=100)
    assert result["id"] == 100


@respx.mock
async def test_create_application(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import create_application

    respx.post(f"{HARVEST_BASE}/candidates/10/applications").mock(
        return_value=httpx.Response(201, json={"id": 55, "job_id": 5, "candidate_id": 10})
    )
    result = await create_application(client, candidate_id=10, job_id=5)
    assert result["id"] == 55
    assert result["candidate_id"] == 10


@respx.mock
async def test_update_application(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import update_application

    respx.patch(f"{HARVEST_BASE}/applications/100").mock(
        return_value=httpx.Response(200, json={"id": 100, "source_id": 7})
    )
    result = await update_application(client, application_id=100, source_id=7)
    assert result["source_id"] == 7


@respx.mock
async def test_delete_application(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import delete_application

    respx.delete(f"{HARVEST_BASE}/applications/100").mock(
        return_value=httpx.Response(200, json={"message": "deleted"})
    )
    result = await delete_application(client, application_id=100)
    assert result["message"] == "deleted"


@respx.mock
async def test_advance_application(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import advance_application

    respx.post(f"{HARVEST_BASE}/applications/100/advance").mock(
        return_value=httpx.Response(200, json={"id": 100, "current_stage": {"id": 3}})
    )
    result = await advance_application(client, application_id=100, from_stage_id=2, to_stage_id=3)
    assert result["id"] == 100


@respx.mock
async def test_move_application(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import move_application

    respx.post(f"{HARVEST_BASE}/applications/100/transfer_to_job").mock(
        return_value=httpx.Response(200, json={"id": 200, "job_id": 99})
    )
    result = await move_application(client, application_id=100, new_job_id=99)
    assert result["job_id"] == 99


@respx.mock
async def test_move_application_same_job(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import move_application_same_job

    respx.post(f"{HARVEST_BASE}/applications/100/move").mock(
        return_value=httpx.Response(200, json={"id": 100, "current_stage": {"id": 4}})
    )
    result = await move_application_same_job(
        client, application_id=100, from_stage_id=3, to_stage_id=4
    )
    assert result["id"] == 100


@respx.mock
async def test_reject_application(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import reject_application

    respx.post(f"{HARVEST_BASE}/applications/100/reject").mock(
        return_value=httpx.Response(200, json={"id": 100, "status": "rejected"})
    )
    result = await reject_application(
        client, application_id=100, rejection_reason_id=5, notes="Not a fit"
    )
    assert result["status"] == "rejected"


@respx.mock
async def test_unreject_application(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import unreject_application

    respx.post(f"{HARVEST_BASE}/applications/100/unreject").mock(
        return_value=httpx.Response(200, json={"id": 100, "status": "active"})
    )
    result = await unreject_application(client, application_id=100)
    assert result["status"] == "active"


@respx.mock
async def test_update_rejection_reason(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import update_rejection_reason

    respx.patch(f"{HARVEST_BASE}/applications/100/reject").mock(
        return_value=httpx.Response(200, json={"id": 100, "rejection_reason": {"id": 9}})
    )
    result = await update_rejection_reason(client, application_id=100, rejection_reason_id=9)
    assert result["rejection_reason"]["id"] == 9


@respx.mock
async def test_hire_application(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import hire_application

    respx.post(f"{HARVEST_BASE}/applications/100/hire").mock(
        return_value=httpx.Response(200, json={"id": 100, "status": "hired"})
    )
    result = await hire_application(
        client, application_id=100, start_date="2026-05-01", opening_id=3
    )
    assert result["status"] == "hired"


@respx.mock
async def test_convert_prospect(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import convert_prospect

    respx.patch(f"{HARVEST_BASE}/applications/100/convert_to_candidate").mock(
        return_value=httpx.Response(200, json={"id": 100, "is_prospect": False})
    )
    result = await convert_prospect(client, application_id=100, job_id=5)
    assert result["is_prospect"] is False


@respx.mock
async def test_add_attachment_to_application(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import add_attachment_to_application

    respx.post(f"{HARVEST_BASE}/applications/100/attachments").mock(
        return_value=httpx.Response(201, json={"filename": "cover.pdf", "type": "cover_letter"})
    )
    result = await add_attachment_to_application(
        client,
        application_id=100,
        filename="cover.pdf",
        type="cover_letter",
        url="https://example.com/cover.pdf",
    )
    assert result["filename"] == "cover.pdf"


@respx.mock
async def test_list_applications_error(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import list_applications

    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(403, json={"message": "Forbidden"})
    )
    result = await list_applications(client)
    assert "error" in result
    assert result["status_code"] == 403


@respx.mock
async def test_get_application_not_found(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import get_application

    respx.get(f"{HARVEST_BASE}/applications/9999").mock(
        return_value=httpx.Response(404, json={"message": "Not found"})
    )
    result = await get_application(client, application_id=9999)
    assert result["status_code"] == 404
