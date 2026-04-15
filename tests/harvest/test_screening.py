"""Tests for harvest/screening.py — composite screening tools."""
from __future__ import annotations

import httpx
import pytest
import respx

from greenhouse_mcp.client import GreenhouseClient

HARVEST_BASE = "https://harvest.greenhouse.io/v1"


@pytest.fixture
def client() -> GreenhouseClient:
    return GreenhouseClient(api_key="test")


# ─── _strip_html ──────────────────────────────────────────────────────


class TestStripHtml:
    def test_basic_tags(self) -> None:
        from greenhouse_mcp.harvest.screening import _strip_html

        assert _strip_html("<p>Hello <b>world</b></p>") == "Hello world"

    def test_br_to_newline(self) -> None:
        from greenhouse_mcp.harvest.screening import _strip_html

        assert _strip_html("Line1<br>Line2<br/>Line3") == "Line1\nLine2\nLine3"

    def test_li_to_bullet(self) -> None:
        from greenhouse_mcp.harvest.screening import _strip_html

        result = _strip_html("<ul><li>First</li><li>Second</li></ul>")
        assert "- First" in result
        assert "- Second" in result

    def test_entity_decoding(self) -> None:
        from greenhouse_mcp.harvest.screening import _strip_html

        assert _strip_html("Tom &amp; Jerry &lt;3") == "Tom & Jerry <3"

    def test_newline_collapsing(self) -> None:
        from greenhouse_mcp.harvest.screening import _strip_html

        result = _strip_html("A\n\n\n\nB")
        assert result == "A\n\nB"

    def test_empty_input(self) -> None:
        from greenhouse_mcp.harvest.screening import _strip_html

        assert _strip_html("") == ""

    def test_none_input(self) -> None:
        from greenhouse_mcp.harvest.screening import _strip_html

        assert _strip_html(None) == ""

    def test_heading_to_double_newline(self) -> None:
        from greenhouse_mcp.harvest.screening import _strip_html

        result = _strip_html("Intro<h2>Section</h2>Body")
        assert "\n\nSection" in result


# ─── _format_date ─────────────────────────────────────────────────────


class TestFormatDate:
    def test_standard_iso(self) -> None:
        from greenhouse_mcp.harvest.screening import _format_date

        assert _format_date("2026-04-15T10:30:00Z") == "April 15, 2026"

    def test_iso_with_timezone(self) -> None:
        from greenhouse_mcp.harvest.screening import _format_date

        assert _format_date("2026-04-15T10:30:00+05:00") == "April 15, 2026"

    def test_date_only(self) -> None:
        from greenhouse_mcp.harvest.screening import _format_date

        assert _format_date("2026-04-15") == "April 15, 2026"

    def test_none_returns_unknown(self) -> None:
        from greenhouse_mcp.harvest.screening import _format_date

        assert _format_date(None) == "Unknown"

    def test_invalid_returns_raw(self) -> None:
        from greenhouse_mcp.harvest.screening import _format_date

        assert _format_date("not-a-date") == "not-a-date"


# ─── _extract_screening_answers ───────────────────────────────────────


class TestExtractScreeningAnswers:
    def test_extracts_pairs(self) -> None:
        from greenhouse_mcp.harvest.screening import _extract_screening_answers

        app = {
            "answers": [
                {"question": "Why us?", "answer": "Great team"},
                {"question": "Location?", "answer": "NYC"},
            ]
        }
        result = _extract_screening_answers(app)
        assert len(result) == 2
        assert result[0] == {"question": "Why us?", "answer": "Great team"}
        assert result[1] == {"question": "Location?", "answer": "NYC"}

    def test_missing_answers_key(self) -> None:
        from greenhouse_mcp.harvest.screening import _extract_screening_answers

        assert _extract_screening_answers({}) == []

    def test_null_answer_placeholder(self) -> None:
        from greenhouse_mcp.harvest.screening import _extract_screening_answers

        app = {"answers": [{"question": "Salary?", "answer": None}]}
        result = _extract_screening_answers(app)
        assert result == [{"question": "Salary?", "answer": "(no answer)"}]

    def test_skips_empty_question(self) -> None:
        from greenhouse_mcp.harvest.screening import _extract_screening_answers

        app = {
            "answers": [
                {"question": "", "answer": "something"},
                {"question": "Real?", "answer": "Yes"},
            ]
        }
        result = _extract_screening_answers(app)
        assert len(result) == 1
        assert result[0]["question"] == "Real?"


# ─── _build_application_history ───────────────────────────────────────


class TestBuildApplicationHistory:
    def test_counts_correctly(self) -> None:
        from greenhouse_mcp.harvest.screening import _build_application_history

        candidate = {
            "applications": [
                {
                    "jobs": [{"name": "SWE"}],
                    "applied_at": "2025-01-01T00:00:00Z",
                    "status": "rejected",
                    "rejection_reason": {"name": "Not qualified"},
                    "current_stage": {"name": "Phone Screen"},
                },
                {
                    "jobs": [{"name": "PM"}],
                    "applied_at": "2025-06-01T00:00:00Z",
                    "status": "active",
                    "rejection_reason": None,
                    "current_stage": {"name": "Onsite"},
                },
            ]
        }
        result = _build_application_history(candidate)
        assert result["total_applications"] == 2
        assert result["rejected"] == 1
        assert result["active"] == 1
        assert result["hired"] == 0
        assert result["is_repeat_rejected"] is False

    def test_flags_repeat_rejection(self) -> None:
        from greenhouse_mcp.harvest.screening import _build_application_history

        candidate = {
            "applications": [
                {
                    "jobs": [{"name": f"Job {i}"}],
                    "applied_at": f"2025-0{i}-01T00:00:00Z",
                    "status": "rejected",
                    "rejection_reason": None,
                    "current_stage": None,
                }
                for i in range(1, 4)
            ]
        }
        result = _build_application_history(candidate)
        assert result["is_repeat_rejected"] is True
        assert result["rejected"] == 3

    def test_not_flagged_when_hired(self) -> None:
        from greenhouse_mcp.harvest.screening import _build_application_history

        candidate = {
            "applications": [
                {
                    "jobs": [{"name": f"Job {i}"}],
                    "applied_at": f"2025-0{i}-01T00:00:00Z",
                    "status": "rejected",
                    "rejection_reason": None,
                    "current_stage": None,
                }
                for i in range(1, 4)
            ]
            + [
                {
                    "jobs": [{"name": "Hired Job"}],
                    "applied_at": "2025-07-01T00:00:00Z",
                    "status": "hired",
                    "rejection_reason": None,
                    "current_stage": {"name": "Offer"},
                }
            ]
        }
        result = _build_application_history(candidate)
        assert result["is_repeat_rejected"] is False
        assert result["hired"] == 1

    def test_empty_applications(self) -> None:
        from greenhouse_mcp.harvest.screening import _build_application_history

        result = _build_application_history({"applications": []})
        assert result["total_applications"] == 0
        assert result["is_repeat_rejected"] is False
        assert result["prior_applications"] == []

    def test_includes_rejection_reason_and_stage(self) -> None:
        from greenhouse_mcp.harvest.screening import _build_application_history

        candidate = {
            "applications": [
                {
                    "jobs": [{"name": "Role A"}],
                    "applied_at": "2025-03-01T00:00:00Z",
                    "status": "rejected",
                    "rejection_reason": {"name": "Over-qualified"},
                    "current_stage": {"name": "Screen"},
                }
            ]
        }
        result = _build_application_history(candidate)
        prior = result["prior_applications"][0]
        assert prior["rejection_reason"] == "Over-qualified"
        assert prior["current_stage"] == "Screen"


# ─── screen_candidate — integration-style tests ──────────────────────


def _mock_application() -> dict:
    """Return a realistic Greenhouse application object."""
    return {
        "id": 100,
        "candidate_id": 200,
        "jobs": [{"id": 300, "name": "Software Engineer"}],
        "applied_at": "2026-04-15T10:00:00Z",
        "status": "active",
        "source": {"public_name": "LinkedIn"},
        "current_stage": {"name": "Phone Screen"},
        "location": {"address": "San Francisco, CA"},
        "answers": [
            {"question": "Where are you located?", "answer": "San Francisco"},
            {"question": "Years of experience?", "answer": "5"},
        ],
    }


def _mock_candidate() -> dict:
    """Return a realistic Greenhouse candidate object."""
    return {
        "id": 200,
        "first_name": "Jane",
        "last_name": "Smith",
        "company": "Acme Corp",
        "title": "Senior Developer",
        "email_addresses": [
            {"value": "jane@example.com", "type": "personal"},
        ],
        "phone_numbers": [
            {"value": "+1-555-123-4567", "type": "mobile"},
        ],
        "social_media_addresses": [
            {"value": "https://linkedin.com/in/janesmith"},
        ],
        "website_addresses": [
            {"value": "https://janesmith.dev"},
        ],
        "tags": [{"name": "strong"}, {"name": "referral"}],
        "addresses": [{"value": "San Francisco, CA", "type": "home"}],
        "attachments": [],
        "applications": [
            {
                "jobs": [{"name": "Software Engineer"}],
                "applied_at": "2026-04-15T10:00:00Z",
                "status": "active",
                "rejection_reason": None,
                "current_stage": {"name": "Phone Screen"},
            }
        ],
    }


def _mock_job_posts_html() -> list:
    """Return a list with one job post containing HTML content."""
    return [
        {
            "id": 400,
            "content": (
                "<h2>About the Role</h2>"
                "<p>We are looking for a <b>Senior Developer</b> "
                "to join our team.</p>"
                "<ul><li>Build features</li><li>Write tests</li></ul>"
            ),
        }
    ]


@respx.mock
@pytest.mark.asyncio
async def test_assembles_complete_screening_package(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.screening import screen_candidate

    # Mock application
    respx.get(f"{HARVEST_BASE}/applications/100").mock(
        return_value=httpx.Response(200, json=_mock_application())
    )
    # Mock candidate
    respx.get(f"{HARVEST_BASE}/candidates/200").mock(
        return_value=httpx.Response(200, json=_mock_candidate())
    )
    # Mock job posts
    respx.get(f"{HARVEST_BASE}/jobs/300/job_posts").mock(
        return_value=httpx.Response(200, json=_mock_job_posts_html())
    )

    result = await screen_candidate(client, application_id=100)

    # Candidate
    assert result["candidate"]["id"] == 200
    assert result["candidate"]["name"] == "Jane Smith"
    assert result["candidate"]["company"] == "Acme Corp"
    assert result["candidate"]["title"] == "Senior Developer"
    assert result["candidate"]["email"] == "jane@example.com"
    assert result["candidate"]["phone"] == "+1-555-123-4567"
    assert "strong" in result["candidate"]["tags"]
    assert "referral" in result["candidate"]["tags"]
    assert result["candidate"]["location"]["location"] == "San Francisco"
    assert result["candidate"]["location"]["confidence"] == "high"

    # Application
    assert result["application"]["id"] == 100
    assert result["application"]["applied_at"] == "April 15, 2026"
    assert result["application"]["source"] == "LinkedIn"
    assert result["application"]["current_stage"] == "Phone Screen"
    assert result["application"]["status"] == "active"

    # Job — HTML stripped
    assert result["job"]["id"] == 300
    assert result["job"]["name"] == "Software Engineer"
    assert "<" not in result["job"]["description"]
    assert "Senior Developer" in result["job"]["description"]
    assert "Build features" in result["job"]["description"]

    # Screening answers
    assert len(result["screening_answers"]) == 2
    assert result["screening_answers"][0]["question"] == "Where are you located?"

    # Resume (no resume on this candidate)
    assert result["resume"]["has_resume"] is False

    # Application history
    assert result["application_history"]["total_applications"] == 1


@respx.mock
@pytest.mark.asyncio
async def test_handles_application_not_found(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.screening import screen_candidate

    respx.get(f"{HARVEST_BASE}/applications/9999").mock(
        return_value=httpx.Response(404, json={"message": "Not found"})
    )

    result = await screen_candidate(client, application_id=9999)
    assert "error" in result


@respx.mock
@pytest.mark.asyncio
async def test_handles_no_resume(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.screening import screen_candidate

    candidate = _mock_candidate()
    candidate["attachments"] = [
        {"type": "cover_letter", "url": "https://example.com/cl.pdf", "filename": "cl.pdf"}
    ]

    respx.get(f"{HARVEST_BASE}/applications/100").mock(
        return_value=httpx.Response(200, json=_mock_application())
    )
    respx.get(f"{HARVEST_BASE}/candidates/200").mock(
        return_value=httpx.Response(200, json=candidate)
    )
    respx.get(f"{HARVEST_BASE}/jobs/300/job_posts").mock(
        return_value=httpx.Response(200, json=_mock_job_posts_html())
    )

    result = await screen_candidate(client, application_id=100)
    assert result["resume"]["has_resume"] is False
    assert result["resume"]["text"] == "(no resume text extracted)"


@respx.mock
@pytest.mark.asyncio
async def test_handles_no_job_posts(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.screening import screen_candidate

    respx.get(f"{HARVEST_BASE}/applications/100").mock(
        return_value=httpx.Response(200, json=_mock_application())
    )
    respx.get(f"{HARVEST_BASE}/candidates/200").mock(
        return_value=httpx.Response(200, json=_mock_candidate())
    )
    respx.get(f"{HARVEST_BASE}/jobs/300/job_posts").mock(
        return_value=httpx.Response(200, json=[])
    )

    result = await screen_candidate(client, application_id=100)
    assert result["job"]["description"] == "(no job post found)"


# ─── fetch_new_applications ──────────────────────────────────────────


def _mock_applications_response() -> list[dict]:
    """Return 3 mock applications across 2 jobs for grouping tests."""
    return [
        {
            "id": 1001,
            "candidate_id": 501,
            "jobs": [{"id": 10, "name": "Software Engineer"}],
            "applied_at": "2026-04-14T09:00:00Z",
            "status": "active",
            "source": {"public_name": "LinkedIn"},
            "current_stage": {"name": "Application Review"},
            "answers": [
                {"question": "Location?", "answer": "NYC"},
            ],
        },
        {
            "id": 1002,
            "candidate_id": 502,
            "jobs": [{"id": 10, "name": "Software Engineer"}],
            "applied_at": "2026-04-14T10:00:00Z",
            "status": "active",
            "source": {"public_name": "Referral"},
            "current_stage": {"name": "Phone Screen"},
            "answers": [],
        },
        {
            "id": 1003,
            "candidate_id": 503,
            "jobs": [{"id": 20, "name": "Product Manager"}],
            "applied_at": "2026-04-13T08:00:00Z",
            "status": "active",
            "source": {"public_name": "Website"},
            "current_stage": {"name": "Application Review"},
            "answers": [
                {"question": "Years of experience?", "answer": "3"},
            ],
        },
    ]


def _mock_candidates_batch() -> list[dict]:
    """Return candidate objects for batch name resolution."""
    return [
        {"id": 501, "first_name": "Alice", "last_name": "Johnson"},
        {"id": 502, "first_name": "Bob", "last_name": "Lee"},
        {"id": 503, "first_name": "Carol", "last_name": "Martinez"},
    ]


@respx.mock
@pytest.mark.asyncio
async def test_fetch_groups_by_job(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.screening import fetch_new_applications

    # Mock applications endpoint
    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=_mock_applications_response())
    )
    # Mock candidates batch lookup
    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=_mock_candidates_batch())
    )

    result = await fetch_new_applications(client, since="2026-04-13")

    assert result["total_new_applications"] == 3
    assert result["jobs_with_new_applications"] == 2
    assert result["since"] == "2026-04-13"
    assert result["status_filter"] == "active"

    by_job = result["by_job"]
    # Software Engineer has 2 candidates, should be first (sorted by count desc)
    assert by_job[0]["job_name"] == "Software Engineer"
    assert by_job[0]["job_id"] == 10
    assert len(by_job[0]["candidates"]) == 2

    assert by_job[1]["job_name"] == "Product Manager"
    assert by_job[1]["job_id"] == 20
    assert len(by_job[1]["candidates"]) == 1

    # Verify candidate names resolved
    swe_candidates = by_job[0]["candidates"]
    names = {c["candidate_name"] for c in swe_candidates}
    assert "Alice Johnson" in names
    assert "Bob Lee" in names

    # Verify screening answers included
    pm_candidate = by_job[1]["candidates"][0]
    assert pm_candidate["candidate_name"] == "Carol Martinez"
    assert len(pm_candidate["screening_answers"]) == 1
    assert pm_candidate["screening_answers"][0]["question"] == "Years of experience?"


@respx.mock
@pytest.mark.asyncio
async def test_fetch_empty_results(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.screening import fetch_new_applications

    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=[])
    )

    result = await fetch_new_applications(client, since="2026-04-13")

    assert result["total_new_applications"] == 0
    assert result["jobs_with_new_applications"] == 0
    assert result["by_job"] == []


@respx.mock
@pytest.mark.asyncio
async def test_fetch_skips_name_resolution(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.screening import fetch_new_applications

    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=_mock_applications_response())
    )
    # No candidates mock — should not be called

    result = await fetch_new_applications(
        client, since="2026-04-13", include_candidate_details=False
    )

    assert result["total_new_applications"] == 3
    # Verify no candidate_name in entries
    for job_entry in result["by_job"]:
        for candidate in job_entry["candidates"]:
            assert "candidate_name" not in candidate

    # Verify candidates endpoint was not called
    candidates_calls = [
        call for call in respx.calls if "/candidates" in str(call.request.url)
    ]
    assert len(candidates_calls) == 0


@respx.mock
@pytest.mark.asyncio
async def test_fetch_with_job_id_filter(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.screening import fetch_new_applications

    apps_route = respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=[_mock_applications_response()[0]])
    )
    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=[_mock_candidates_batch()[0]])
    )

    result = await fetch_new_applications(client, since="2026-04-13", job_id=10)

    assert result["total_new_applications"] == 1
    # Verify job_id was passed in the request params
    request = apps_route.calls[0].request
    assert "job_id=10" in str(request.url)


@respx.mock
@pytest.mark.asyncio
async def test_fetch_handles_api_error(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.screening import fetch_new_applications

    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(500, json={"message": "Internal Server Error"})
    )

    result = await fetch_new_applications(client, since="2026-04-13")

    assert "error" in result
