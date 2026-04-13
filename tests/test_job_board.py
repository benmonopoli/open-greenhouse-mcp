"""Tests for job_board/ modules."""
from __future__ import annotations

import httpx
import pytest
import respx

from greenhouse_mcp.client import GreenhouseClient

BOARD_BASE = "https://boards-api.greenhouse.io/v1/boards/test-board"


@pytest.fixture
def client() -> GreenhouseClient:
    return GreenhouseClient(board_token="test-board")


@respx.mock
async def test_get_board(client: GreenhouseClient) -> None:
    from greenhouse_mcp.job_board.board import get_board

    respx.get(f"{BOARD_BASE}").mock(
        return_value=httpx.Response(200, json={"name": "Acme Jobs"})
    )
    result = await get_board(client)
    assert result["name"] == "Acme Jobs"


@respx.mock
async def test_list_board_jobs(client: GreenhouseClient) -> None:
    from greenhouse_mcp.job_board.jobs import list_board_jobs

    respx.get(f"{BOARD_BASE}/jobs").mock(
        return_value=httpx.Response(200, json={"jobs": [{"id": 1}]})
    )
    result = await list_board_jobs(client)
    assert "jobs" in result


@respx.mock
async def test_get_board_job(client: GreenhouseClient) -> None:
    from greenhouse_mcp.job_board.jobs import get_board_job

    respx.get(f"{BOARD_BASE}/jobs/42").mock(
        return_value=httpx.Response(200, json={"id": 42, "title": "Engineer"})
    )
    result = await get_board_job(client, job_id=42)
    assert result["id"] == 42


@respx.mock
async def test_list_board_departments(client: GreenhouseClient) -> None:
    from greenhouse_mcp.job_board.departments import list_board_departments

    respx.get(f"{BOARD_BASE}/departments").mock(
        return_value=httpx.Response(200, json={"departments": [{"id": 1}]})
    )
    result = await list_board_departments(client)
    assert "departments" in result


@respx.mock
async def test_get_board_department(client: GreenhouseClient) -> None:
    from greenhouse_mcp.job_board.departments import get_board_department

    respx.get(f"{BOARD_BASE}/departments/5").mock(
        return_value=httpx.Response(200, json={"id": 5, "name": "Eng"})
    )
    result = await get_board_department(client, department_id=5)
    assert result["id"] == 5


@respx.mock
async def test_list_board_offices(client: GreenhouseClient) -> None:
    from greenhouse_mcp.job_board.offices import list_board_offices

    respx.get(f"{BOARD_BASE}/offices").mock(
        return_value=httpx.Response(200, json={"offices": [{"id": 1}]})
    )
    result = await list_board_offices(client)
    assert "offices" in result


@respx.mock
async def test_get_board_office(client: GreenhouseClient) -> None:
    from greenhouse_mcp.job_board.offices import get_board_office

    respx.get(f"{BOARD_BASE}/offices/3").mock(
        return_value=httpx.Response(200, json={"id": 3, "name": "NYC"})
    )
    result = await get_board_office(client, office_id=3)
    assert result["id"] == 3


@respx.mock
async def test_list_prospect_post_sections(client: GreenhouseClient) -> None:
    from greenhouse_mcp.job_board.prospects import list_prospect_post_sections

    respx.get(f"{BOARD_BASE}/prospect_posts").mock(
        return_value=httpx.Response(200, json={"prospect_posts": []})
    )
    result = await list_prospect_post_sections(client)
    assert "prospect_posts" in result


@respx.mock
async def test_get_prospect_post_section(client: GreenhouseClient) -> None:
    from greenhouse_mcp.job_board.prospects import get_prospect_post_section

    respx.get(f"{BOARD_BASE}/prospect_posts/7").mock(
        return_value=httpx.Response(200, json={"id": 7})
    )
    result = await get_prospect_post_section(client, section_id=7)
    assert result["id"] == 7


@respx.mock
async def test_list_board_degrees(client: GreenhouseClient) -> None:
    from greenhouse_mcp.job_board.educations import list_board_degrees

    respx.get(f"{BOARD_BASE}/education/degrees").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "BS"}])
    )
    result = await list_board_degrees(client)
    assert isinstance(result, list)


@respx.mock
async def test_list_board_disciplines(client: GreenhouseClient) -> None:
    from greenhouse_mcp.job_board.educations import list_board_disciplines

    respx.get(f"{BOARD_BASE}/education/disciplines").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "CS"}])
    )
    result = await list_board_disciplines(client)
    assert isinstance(result, list)


@respx.mock
async def test_list_board_schools(client: GreenhouseClient) -> None:
    from greenhouse_mcp.job_board.educations import list_board_schools

    respx.get(f"{BOARD_BASE}/education/schools").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "MIT"}])
    )
    result = await list_board_schools(client)
    assert isinstance(result, list)


@respx.mock
async def test_submit_application() -> None:
    from greenhouse_mcp.job_board.applications import submit_application

    respx.post(f"{BOARD_BASE}/applications").mock(
        return_value=httpx.Response(200, json={"id": 99, "status": "received"})
    )
    client = GreenhouseClient(api_key="test-key", board_token="test-board")
    result = await submit_application(
        client,
        job_id=1,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
    )
    assert result["status"] == "received"
