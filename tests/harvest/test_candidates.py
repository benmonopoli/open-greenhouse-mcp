"""Tests for harvest/candidates.py."""
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
async def test_list_candidates(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import list_candidates

    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "first_name": "Alice"}])
    )
    result = await list_candidates(client)
    assert result["items"] == [{"id": 1, "first_name": "Alice"}]
    assert result["has_next"] is False


@respx.mock
async def test_list_candidates_with_filters(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import list_candidates

    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=[{"id": 2}])
    )
    result = await list_candidates(client, email="alice@example.com", candidate_ids=[2])
    assert result["items"] == [{"id": 2}]


@respx.mock
async def test_get_candidate(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import get_candidate

    respx.get(f"{HARVEST_BASE}/candidates/42").mock(
        return_value=httpx.Response(200, json={"id": 42, "first_name": "Bob"})
    )
    result = await get_candidate(client, candidate_id=42)
    assert result["id"] == 42


@respx.mock
async def test_create_candidate(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import create_candidate

    respx.post(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(
            201, json={"id": 99, "first_name": "Carol", "last_name": "Smith"}
        )
    )
    result = await create_candidate(
        client,
        first_name="Carol",
        last_name="Smith",
        company="Acme",
        email_addresses=[{"value": "carol@example.com", "type": "personal"}],
    )
    assert result["id"] == 99
    assert result["first_name"] == "Carol"


@respx.mock
async def test_update_candidate(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import update_candidate

    respx.patch(f"{HARVEST_BASE}/candidates/42").mock(
        return_value=httpx.Response(200, json={"id": 42, "title": "Engineer"})
    )
    result = await update_candidate(client, candidate_id=42, title="Engineer")
    assert result["title"] == "Engineer"


@respx.mock
async def test_delete_candidate(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import delete_candidate

    respx.delete(f"{HARVEST_BASE}/candidates/42").mock(
        return_value=httpx.Response(200, json={"message": "deleted"})
    )
    result = await delete_candidate(client, candidate_id=42)
    assert result["message"] == "deleted"


@respx.mock
async def test_merge_candidates(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import merge_candidates

    respx.put(f"{HARVEST_BASE}/candidates/merge").mock(
        return_value=httpx.Response(200, json={"id": 1})
    )
    result = await merge_candidates(client, primary_candidate_id=1, duplicate_candidate_id=2)
    assert result["id"] == 1


@respx.mock
async def test_anonymize_candidate(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import anonymize_candidate

    respx.put(f"{HARVEST_BASE}/candidates/42/anonymize").mock(
        return_value=httpx.Response(200, json={"id": 42})
    )
    result = await anonymize_candidate(client, candidate_id=42, fields=["full_name", "email"])
    assert result["id"] == 42


@respx.mock
async def test_add_prospect(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import add_prospect

    respx.post(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(201, json={"id": 77, "is_prospect": True})
    )
    result = await add_prospect(client, first_name="Dave", last_name="Jones")
    assert result["is_prospect"] is True


@respx.mock
async def test_add_education(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import add_education

    respx.post(f"{HARVEST_BASE}/candidates/42/educations").mock(
        return_value=httpx.Response(201, json={"id": 5, "school_id": 10})
    )
    result = await add_education(client, candidate_id=42, school_id=10)
    assert result["school_id"] == 10


@respx.mock
async def test_remove_education(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import remove_education

    respx.delete(f"{HARVEST_BASE}/candidates/42/educations/5").mock(
        return_value=httpx.Response(200, json={})
    )
    result = await remove_education(client, candidate_id=42, education_id=5)
    assert result == {}


@respx.mock
async def test_add_employment(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import add_employment

    respx.post(f"{HARVEST_BASE}/candidates/42/employments").mock(
        return_value=httpx.Response(201, json={"id": 3, "company_name": "Acme"})
    )
    result = await add_employment(client, candidate_id=42, company_name="Acme", title="Dev")
    assert result["company_name"] == "Acme"


@respx.mock
async def test_remove_employment(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import remove_employment

    respx.delete(f"{HARVEST_BASE}/candidates/42/employments/3").mock(
        return_value=httpx.Response(200, json={})
    )
    result = await remove_employment(client, candidate_id=42, employment_id=3)
    assert result == {}


@respx.mock
async def test_add_attachment(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import add_attachment

    respx.post(f"{HARVEST_BASE}/candidates/42/attachments").mock(
        return_value=httpx.Response(201, json={"filename": "resume.pdf", "type": "resume"})
    )
    result = await add_attachment(
        client, candidate_id=42, filename="resume.pdf", type="resume", url="https://example.com/resume.pdf"
    )
    assert result["filename"] == "resume.pdf"


@respx.mock
async def test_add_note_to_candidate(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import add_note_to_candidate

    respx.post(f"{HARVEST_BASE}/candidates/42/activity_feed/notes").mock(
        return_value=httpx.Response(201, json={"body": "Great candidate", "visibility": "private"})
    )
    result = await add_note_to_candidate(client, candidate_id=42, body="Great candidate")
    assert result["body"] == "Great candidate"
    assert result["visibility"] == "private"


@respx.mock
async def test_add_email_note_to_candidate(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import add_email_note_to_candidate

    respx.post(f"{HARVEST_BASE}/candidates/42/activity_feed/emails").mock(
        return_value=httpx.Response(201, json={"subject": "Offer", "to": "alice@example.com"})
    )
    result = await add_email_note_to_candidate(
        client,
        candidate_id=42,
        to="alice@example.com",
        from_="recruiter@company.com",
        subject="Offer",
        body="We'd like to extend an offer.",
    )
    assert result["subject"] == "Offer"


@respx.mock
async def test_list_candidates_error(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import list_candidates

    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(401, json={"message": "Unauthorized"})
    )
    result = await list_candidates(client)
    assert "error" in result
    assert result["status_code"] == 401


@respx.mock
async def test_get_candidate_not_found(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import get_candidate

    respx.get(f"{HARVEST_BASE}/candidates/9999").mock(
        return_value=httpx.Response(404, json={"message": "Not found"})
    )
    result = await get_candidate(client, candidate_id=9999)
    assert result["status_code"] == 404
