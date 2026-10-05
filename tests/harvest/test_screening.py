"""Tests for harvest/screening.py — composite screening tools."""
from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx

from greenhouse_mcp.client import GreenhouseClient

HARVEST_BASE = "https://harvest.greenhouse.io/v3"


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

        apps = [
            {
                "id": 1,
                "job_id": 10,
                "created_at": "2025-01-01T00:00:00Z",
                "status": "rejected",
                "rejection_reason_id": 7,
                "stage_name": "Phone Screen",
            },
            {
                "id": 2,
                "job_id": 20,
                "created_at": "2025-06-01T00:00:00Z",
                "status": "in_process",
                "rejection_reason_id": None,
                "stage_name": "Onsite",
            },
        ]
        result = _build_application_history(apps, {10: "SWE", 20: "PM"}, {7: "Not qualified"})
        assert result["total_applications"] == 2
        assert result["rejected"] == 1
        assert result["active"] == 1
        assert result["hired"] == 0
        assert result["is_repeat_rejected"] is False
        # Most recent first, names resolved, v3 status mapped to "active"
        first, second = result["prior_applications"]
        assert first["job"] == "PM" and first["status"] == "active"
        assert second["job"] == "SWE"
        assert second["rejection_reason"] == "Not qualified"
        assert second["current_stage"] == "Phone Screen"
        assert second["applied"] == "January 1, 2025"

    def test_flags_repeat_rejection(self) -> None:
        from greenhouse_mcp.harvest.screening import _build_application_history

        apps = [
            {"id": i, "job_id": i, "created_at": f"2025-0{i}-01T00:00:00Z", "status": "rejected"}
            for i in range(1, 4)
        ]
        result = _build_application_history(apps)
        assert result["is_repeat_rejected"] is True
        assert result["rejected"] == 3

    def test_not_flagged_when_hired(self) -> None:
        from greenhouse_mcp.harvest.screening import _build_application_history

        apps: list[dict[str, Any]] = [
            {"id": i, "job_id": i, "created_at": f"2025-0{i}-01T00:00:00Z", "status": "rejected"}
            for i in range(1, 4)
        ]
        apps.append({"id": 9, "job_id": 9, "status": "hired", "stage_name": "Offer"})
        result = _build_application_history(apps)
        assert result["is_repeat_rejected"] is False
        assert result["hired"] == 1

    def test_empty_applications(self) -> None:
        from greenhouse_mcp.harvest.screening import _build_application_history

        result = _build_application_history([])
        assert result["total_applications"] == 0
        assert result["is_repeat_rejected"] is False
        assert result["prior_applications"] == []

    def test_unknown_and_prospect_jobs(self) -> None:
        from greenhouse_mcp.harvest.screening import _build_application_history

        apps = [
            {"id": 1, "job_id": None, "prospect": True, "status": "in_process"},
            {"id": 2, "job_id": 55, "status": "in_process"},
        ]
        jobs = {a["job"] for a in _build_application_history(apps)["prior_applications"]}
        assert jobs == {"Prospect (no job)", "Unknown"}


class TestPickHelpers:
    def test_pick_job_post_prefers_live_external(self) -> None:
        from greenhouse_mcp.harvest.screening import _pick_job_post

        posts = [
            {"id": 1, "internal": True, "live": True, "content": "internal"},
            {"id": 2, "internal": False, "live": False, "content": "draft"},
            {"id": 3, "internal": False, "live": True, "content": "live"},
            {"id": 4, "internal": False, "live": True, "content": None},
        ]
        assert _pick_job_post(posts)["id"] == 3  # type: ignore[index]
        assert _pick_job_post(posts[:2])["id"] == 2  # type: ignore[index]
        assert _pick_job_post([posts[3]]) is None

    def test_pick_resume_prefers_this_application_then_latest(self) -> None:
        from greenhouse_mcp.harvest.screening import _pick_resume

        atts = [
            {"id": 1, "application_id": 100, "type": "resume", "url": "u1",
             "created_at": "2025-01-01T00:00:00Z"},
            {"id": 2, "application_id": 999, "type": "resume", "url": "u2",
             "created_at": "2026-01-01T00:00:00Z"},
            {"id": 3, "application_id": 100, "type": "cover_letter", "url": "u3",
             "created_at": "2026-02-01T00:00:00Z"},
        ]
        assert _pick_resume(atts, 100)["id"] == 1  # type: ignore[index]
        assert _pick_resume(atts, 555)["id"] == 2  # type: ignore[index]
        assert _pick_resume([atts[2]], 100) is None

    def test_tag_names_accepts_v3_strings(self) -> None:
        from greenhouse_mcp.harvest.screening import _tag_names

        assert _tag_names({"tags": ["strong", "", "referral"]}) == ["strong", "referral"]
        assert _tag_names({"tags": None}) == []


# ─── screen_candidate — integration-style tests ──────────────────────


def _mock_application() -> dict[str, Any]:
    """A v3 application record."""
    return {
        "id": 100,
        "candidate_id": 200,
        "job_id": 300,
        "source_id": 40,
        "created_at": "2026-04-15T10:00:00Z",
        "last_activity_at": "2026-04-16T10:00:00Z",
        "status": "in_process",
        "stage_id": 9100,
        "job_interview_stage_id": 900,
        "stage_name": "Phone Screen",
        "rejection_reason_id": None,
        "prospect": False,
        "location_address": "San Francisco, CA",
        "answers": [
            {"question": "Where are you located?", "answer": "San Francisco"},
            {"question": "Years of experience?", "answer": "5"},
        ],
    }


def _mock_candidate() -> dict[str, Any]:
    """A v3 candidate record (no applications / attachments embedded)."""
    return {
        "id": 200,
        "first_name": "Jane",
        "last_name": "Smith",
        "preferred_name": None,
        "company": "Acme Corp",
        "title": "Senior Developer",
        "email_addresses": [{"value": "jane@example.com", "type": "personal"}],
        "phone_numbers": [{"value": "+1-555-123-4567", "type": "mobile"}],
        "social_media_addresses": [{"value": "https://linkedin.com/in/janesmith"}],
        "website_addresses": [{"value": "https://janesmith.dev", "type": "personal"}],
        "tags": ["strong", "referral"],
        "addresses": [{"value": "San Francisco, CA", "type": "home"}],
    }


def _mock_job_posts_html() -> list[dict[str, Any]]:
    return [
        {
            "id": 400,
            "job_id": 300,
            "internal": False,
            "live": True,
            "content": (
                "<h2>About the Role</h2>"
                "<p>We are looking for a <b>Senior Developer</b> "
                "to join our team.</p>"
                "<ul><li>Build features</li><li>Write tests</li></ul>"
            ),
        }
    ]


def _prior_application() -> dict[str, Any]:
    return {
        "id": 50,
        "candidate_id": 200,
        "job_id": 301,
        "created_at": "2025-01-10T10:00:00Z",
        "status": "rejected",
        "rejection_reason_id": 7,
        "stage_name": "Application Review",
    }


def _mock_screening_api(
    *,
    application: dict[str, Any] | None = None,
    candidate: dict[str, Any] | None = None,
    posts: list[dict[str, Any]] | None = None,
    attachments: list[dict[str, Any]] | None = None,
) -> dict[str, respx.Route]:
    app = application or _mock_application()

    def applications(request: httpx.Request) -> httpx.Response:
        params = request.url.params
        if params.get("ids") == "100":
            return httpx.Response(200, json=[app])
        if params.get("candidate_ids") == "200":
            return httpx.Response(200, json=[app, _prior_application()])
        return httpx.Response(200, json=[])

    return {
        "applications": respx.get(f"{HARVEST_BASE}/applications").mock(side_effect=applications),
        "candidates": respx.get(f"{HARVEST_BASE}/candidates").mock(
            return_value=httpx.Response(200, json=[candidate or _mock_candidate()])
        ),
        "job_posts": respx.get(f"{HARVEST_BASE}/job_posts").mock(
            return_value=httpx.Response(
                200, json=_mock_job_posts_html() if posts is None else posts
            )
        ),
        "attachments": respx.get(f"{HARVEST_BASE}/attachments").mock(
            return_value=httpx.Response(200, json=attachments or [])
        ),
        "jobs": respx.get(f"{HARVEST_BASE}/jobs").mock(
            return_value=httpx.Response(
                200,
                json=[{"id": 300, "name": "Software Engineer"}, {"id": 301, "name": "QA Lead"}],
            )
        ),
        "sources": respx.get(f"{HARVEST_BASE}/sources").mock(
            return_value=httpx.Response(
                200, json=[{"id": 40, "name": "LinkedIn", "type": {"id": 1, "name": "Prospecting"}}]
            )
        ),
        "rejection_reasons": respx.get(f"{HARVEST_BASE}/rejection_reasons").mock(
            return_value=httpx.Response(200, json=[{"id": 7, "name": "Lacking skills"}])
        ),
    }


@respx.mock
@pytest.mark.asyncio
async def test_assembles_complete_screening_package(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.screening import screen_candidate

    routes = _mock_screening_api()
    result = await screen_candidate(client, application_id=100)

    # Candidate
    assert result["candidate"]["id"] == 200
    assert result["candidate"]["name"] == "Jane Smith"
    assert result["candidate"]["company"] == "Acme Corp"
    assert result["candidate"]["title"] == "Senior Developer"
    assert result["candidate"]["email"] == "jane@example.com"
    assert result["candidate"]["phone"] == "+1-555-123-4567"
    assert result["candidate"]["tags"] == ["strong", "referral"]
    assert result["candidate"]["links"]["linkedin"] == "https://linkedin.com/in/janesmith"
    assert result["candidate"]["location"]["location"] == "San Francisco"
    assert result["candidate"]["location"]["confidence"] == "high"

    # Application — names resolved from ids
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

    assert len(result["screening_answers"]) == 2
    assert result["screening_answers"][0]["question"] == "Where are you located?"
    assert result["resume"]["has_resume"] is False

    history = result["application_history"]
    assert history["total_applications"] == 2
    assert history["rejected"] == 1 and history["active"] == 1
    prior = {p["application_id"]: p for p in history["prior_applications"]}
    assert prior[50]["job"] == "QA Lead"
    assert prior[50]["rejection_reason"] == "Lacking skills"

    # v3 query params
    assert routes["candidates"].calls[0].request.url.params["ids"] == "200"
    assert routes["job_posts"].calls[0].request.url.params["job_ids"] == "300"
    att_params = routes["attachments"].calls[0].request.url.params
    assert att_params["candidate_ids"] == "200" and att_params["type"] == "resume"
    assert routes["sources"].calls[0].request.url.params["ids"] == "40"
    assert set(routes["jobs"].calls[0].request.url.params["ids"].split(",")) == {"300", "301"}


@respx.mock
@pytest.mark.asyncio
async def test_location_falls_back_to_location_address(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.screening import screen_candidate

    app = _mock_application()
    app["answers"] = [{"question": "Years of experience?", "answer": "5"}]
    _mock_screening_api(application=app)
    result = await screen_candidate(client, application_id=100)
    assert result["candidate"]["location"] == {
        "location": "San Francisco, CA",
        "source": "application_location",
        "confidence": "high",
    }


@respx.mock
@pytest.mark.asyncio
async def test_handles_application_not_found(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.screening import screen_candidate

    respx.get(f"{HARVEST_BASE}/applications").mock(return_value=httpx.Response(200, json=[]))
    result = await screen_candidate(client, application_id=9999)
    assert "error" in result
    assert result["detail"]["status_code"] == 404


@respx.mock
@pytest.mark.asyncio
async def test_handles_candidate_error(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.screening import screen_candidate

    _mock_screening_api()
    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(403, json={"message": "Forbidden"})
    )
    result = await screen_candidate(client, application_id=100)
    assert "error" in result
    assert "candidate" in result["error"].lower()


@respx.mock
@pytest.mark.asyncio
async def test_downloads_resume_text(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.screening import screen_candidate

    _mock_screening_api(
        attachments=[
            {"id": 1, "application_id": 100, "candidate_id": 200, "type": "resume",
             "filename": "jane.txt", "url": "https://files.example.com/jane.txt",
             "created_at": "2026-04-15T10:00:00Z"},
        ]
    )
    respx.get("https://files.example.com/jane.txt").mock(
        return_value=httpx.Response(
            200, text="Jane Smith\nBased in Oakland, CA", headers={"content-type": "text/plain"}
        )
    )
    result = await screen_candidate(client, application_id=100)
    assert result["resume"]["has_resume"] is True
    assert result["resume"]["filename"] == "jane.txt"
    assert "Oakland" in result["resume"]["text"]


@respx.mock
@pytest.mark.asyncio
async def test_handles_no_resume(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.screening import screen_candidate

    _mock_screening_api(
        attachments=[
            {"id": 1, "application_id": 100, "type": "cover_letter",
             "url": "https://example.com/cl.pdf", "filename": "cl.pdf"}
        ]
    )
    result = await screen_candidate(client, application_id=100)
    assert result["resume"]["has_resume"] is False
    assert result["resume"]["text"] == "(no resume text extracted)"


@respx.mock
@pytest.mark.asyncio
async def test_handles_no_job_posts(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.screening import screen_candidate

    _mock_screening_api(posts=[])
    result = await screen_candidate(client, application_id=100)
    assert result["job"]["description"] == "(no job post found)"


@respx.mock
@pytest.mark.asyncio
async def test_prospect_application_without_job(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.screening import screen_candidate

    app = _mock_application()
    app.update({"job_id": None, "prospect": True, "source_id": None})
    routes = _mock_screening_api(application=app)
    result = await screen_candidate(client, application_id=100)
    assert result["job"] == {"id": None, "name": "Unknown", "description": "(no job post found)"}
    assert result["application"]["source"] == "Unknown"
    assert not routes["job_posts"].called
    assert not routes["sources"].called


# ─── fetch_new_applications ──────────────────────────────────────────


def _mock_applications_response() -> list[dict[str, Any]]:
    """3 v3 applications across 2 jobs for grouping tests."""
    return [
        {
            "id": 1001,
            "candidate_id": 501,
            "job_id": 10,
            "source_id": 1,
            "created_at": "2026-04-14T09:00:00Z",
            "status": "in_process",
            "stage_name": "Application Review",
            "location_address": "New York",
            "answers": [{"question": "Location?", "answer": "NYC"}],
        },
        {
            "id": 1002,
            "candidate_id": 502,
            "job_id": 10,
            "source_id": 2,
            "created_at": "2026-04-14T10:00:00Z",
            "status": "in_process",
            "stage_name": "Phone Screen",
            "answers": None,
        },
        {
            "id": 1003,
            "candidate_id": 503,
            "job_id": 20,
            "source_id": None,
            "created_at": "2026-04-13T08:00:00Z",
            "status": "in_process",
            "stage_name": "Application Review",
            "answers": [{"question": "Years of experience?", "answer": "3"}],
        },
    ]


def _mock_candidates_batch() -> list[dict[str, Any]]:
    return [
        {"id": 501, "first_name": "Alice", "last_name": "Johnson"},
        {"id": 502, "first_name": "Bob", "last_name": "Lee"},
        {"id": 503, "first_name": "Carol", "last_name": "Martinez"},
    ]


def _mock_digest_lookups() -> dict[str, respx.Route]:
    return {
        "jobs": respx.get(f"{HARVEST_BASE}/jobs").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"id": 10, "name": "Software Engineer"},
                    {"id": 20, "name": "Product Manager"},
                ],
            )
        ),
        "sources": respx.get(f"{HARVEST_BASE}/sources").mock(
            return_value=httpx.Response(
                200, json=[{"id": 1, "name": "LinkedIn"}, {"id": 2, "name": "Referral"}]
            )
        ),
    }


@respx.mock
@pytest.mark.asyncio
async def test_fetch_groups_by_job(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.screening import fetch_new_applications

    apps_route = respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=_mock_applications_response())
    )
    cand_route = respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=_mock_candidates_batch())
    )
    _mock_digest_lookups()

    result = await fetch_new_applications(client, since="2026-04-13")

    params = apps_route.calls[0].request.url.params
    assert params["created_at[gte]"] == "2026-04-13T00:00:00Z"
    assert params["status"] == "active"
    assert "created_after" not in params
    assert cand_route.calls[0].request.url.params["ids"] == "501,502,503"

    assert result["total_new_applications"] == 3
    assert result["jobs_with_new_applications"] == 2
    assert result["since"] == "2026-04-13"
    assert result["status_filter"] == "active"

    by_job = result["by_job"]
    assert by_job[0]["job_name"] == "Software Engineer"
    assert by_job[0]["job_id"] == 10
    assert len(by_job[0]["candidates"]) == 2
    assert by_job[1]["job_name"] == "Product Manager"
    assert by_job[1]["job_id"] == 20

    swe = {c["candidate_name"]: c for c in by_job[0]["candidates"]}
    assert set(swe) == {"Alice Johnson", "Bob Lee"}
    assert swe["Alice Johnson"]["source"] == "LinkedIn"
    assert swe["Alice Johnson"]["current_stage"] == "Application Review"
    assert swe["Alice Johnson"]["applied_at"] == "April 14, 2026"
    assert swe["Alice Johnson"]["location"] == "New York"
    assert swe["Bob Lee"]["source"] == "Referral"
    assert swe["Bob Lee"]["screening_answers"] == []

    pm_candidate = by_job[1]["candidates"][0]
    assert pm_candidate["candidate_name"] == "Carol Martinez"
    assert pm_candidate["source"] == "Unknown"
    assert pm_candidate["screening_answers"][0]["question"] == "Years of experience?"


@respx.mock
@pytest.mark.asyncio
async def test_fetch_empty_results(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.screening import fetch_new_applications

    respx.get(f"{HARVEST_BASE}/applications").mock(return_value=httpx.Response(200, json=[]))

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
    _mock_digest_lookups()

    result = await fetch_new_applications(
        client, since="2026-04-13", include_candidate_details=False
    )

    assert result["total_new_applications"] == 3
    for job_entry in result["by_job"]:
        for candidate in job_entry["candidates"]:
            assert "candidate_name" not in candidate
    assert not [c for c in respx.calls if "/candidates" in str(c.request.url)]


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
    _mock_digest_lookups()

    result = await fetch_new_applications(
        client, since="2026-04-13T12:00:00Z", job_id=10, status="rejected"
    )

    assert result["total_new_applications"] == 1
    params = apps_route.calls[0].request.url.params
    assert params["job_ids"] == "10"
    assert "job_id" not in params
    assert params["status"] == "rejected"
    assert params["created_at[gte]"] == "2026-04-13T12:00:00Z"


@respx.mock
@pytest.mark.asyncio
async def test_fetch_handles_api_error(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.screening import fetch_new_applications

    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(500, json={"message": "Internal Server Error"})
    )

    result = await fetch_new_applications(client, since="2026-04-13")

    assert "error" in result
