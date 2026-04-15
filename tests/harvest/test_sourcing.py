"""Tests for harvest/sourcing.py — composite sourcing tools."""
from __future__ import annotations

import httpx
import pytest
import respx

from greenhouse_mcp.client import GreenhouseClient

HARVEST_BASE = "https://harvest.greenhouse.io/v1"


@pytest.fixture
def client() -> GreenhouseClient:
    return GreenhouseClient(api_key="test")


# ─── _calculate_experience_years ─────────────────────────────────────


class TestCalculateExperienceYears:
    def test_no_employments(self) -> None:
        from greenhouse_mcp.harvest.sourcing import (
            _calculate_experience_years,
        )

        assert _calculate_experience_years([]) is None

    def test_single_employment_with_dates(self) -> None:
        from greenhouse_mcp.harvest.sourcing import (
            _calculate_experience_years,
        )

        result = _calculate_experience_years([
            {
                "start_date": "2020-01-01",
                "end_date": "2023-01-01",
            }
        ])
        assert result is not None
        assert 2.9 <= result <= 3.1

    def test_multiple_employments(self) -> None:
        from greenhouse_mcp.harvest.sourcing import (
            _calculate_experience_years,
        )

        result = _calculate_experience_years([
            {
                "start_date": "2018-01-01",
                "end_date": "2020-01-01",
            },
            {
                "start_date": "2020-06-01",
                "end_date": "2023-06-01",
            },
        ])
        assert result is not None
        assert 4.9 <= result <= 5.1

    def test_missing_dates_returns_none(self) -> None:
        from greenhouse_mcp.harvest.sourcing import (
            _calculate_experience_years,
        )

        result = _calculate_experience_years([
            {"company_name": "Acme", "title": "Dev"},
        ])
        assert result is None

    def test_current_employment_no_end_date(self) -> None:
        from greenhouse_mcp.harvest.sourcing import (
            _calculate_experience_years,
        )

        result = _calculate_experience_years([
            {"start_date": "2020-01-01", "end_date": None},
        ])
        assert result is not None
        # Should be at least 4 years from 2020 to today (2026)
        assert result >= 4.0


# ─── _matches_keywords ───────────────────────────────────────────────


class TestMatchesKeywords:
    def test_basic_match(self) -> None:
        from greenhouse_mcp.harvest.sourcing import _matches_keywords

        result = _matches_keywords("Senior Engineer", ["engineer"])
        assert result == ["engineer"]

    def test_case_insensitive(self) -> None:
        from greenhouse_mcp.harvest.sourcing import _matches_keywords

        result = _matches_keywords("Senior ENGINEER", ["engineer"])
        assert result == ["engineer"]

    def test_no_match(self) -> None:
        from greenhouse_mcp.harvest.sourcing import _matches_keywords

        result = _matches_keywords("Product Manager", ["engineer"])
        assert result == []

    def test_multiple_matches(self) -> None:
        from greenhouse_mcp.harvest.sourcing import _matches_keywords

        result = _matches_keywords(
            "Senior Software Engineer at Google",
            ["senior", "engineer", "manager"],
        )
        assert "senior" in result
        assert "engineer" in result
        assert "manager" not in result

    def test_empty_keywords(self) -> None:
        from greenhouse_mcp.harvest.sourcing import _matches_keywords

        assert _matches_keywords("Some text", []) == []

    def test_empty_text(self) -> None:
        from greenhouse_mcp.harvest.sourcing import _matches_keywords

        assert _matches_keywords("", ["engineer"]) == []


# ─── _build_candidate_profile ────────────────────────────────────────


class TestBuildCandidateProfile:
    def test_complete_candidate(self) -> None:
        from greenhouse_mcp.harvest.sourcing import (
            _build_candidate_profile,
        )

        candidate = {
            "id": 123,
            "first_name": "Jane",
            "last_name": "Doe",
            "title": "Senior Developer",
            "company": "Acme Corp",
            "email_addresses": [
                {"value": "jane@example.com", "type": "personal"},
            ],
            "tags": [{"name": "Python"}, {"name": "Senior"}],
            "employments": [
                {
                    "company_name": "Acme Corp",
                    "title": "Senior Developer",
                    "start_date": "2020-01-01",
                    "end_date": "2023-06-15",
                },
            ],
            "educations": [
                {
                    "school_name": "MIT",
                    "degree": "BS",
                    "discipline": "Computer Science",
                },
            ],
        }

        profile = _build_candidate_profile(candidate)
        assert profile["id"] == 123
        assert profile["name"] == "Jane Doe"
        assert profile["title"] == "Senior Developer"
        assert profile["company"] == "Acme Corp"
        assert profile["email"] == "jane@example.com"
        assert "Python" in profile["tags"]
        assert "Senior" in profile["tags"]
        assert len(profile["employments"]) == 1
        assert profile["employments"][0]["company"] == "Acme Corp"
        assert len(profile["educations"]) == 1
        assert profile["educations"][0]["school"] == "MIT"
        assert profile["experience_years"] is not None

    def test_minimal_candidate(self) -> None:
        from greenhouse_mcp.harvest.sourcing import (
            _build_candidate_profile,
        )

        candidate = {
            "id": 456,
            "first_name": "Bob",
            "last_name": "",
        }

        profile = _build_candidate_profile(candidate)
        assert profile["id"] == 456
        assert profile["name"] == "Bob"
        assert profile["title"] == ""
        assert profile["company"] == ""
        assert profile["email"] is None
        assert profile["tags"] == []
        assert profile["employments"] == []
        assert profile["educations"] == []
        assert profile["experience_years"] is None


# ─── _matches_filters ────────────────────────────────────────────────


class TestMatchesFilters:
    def _make_profile(self) -> dict:
        return {
            "id": 1,
            "name": "Jane Doe",
            "title": "Senior Engineer",
            "company": "Google",
            "email": "jane@example.com",
            "tags": ["Python", "Backend"],
            "employments": [
                {
                    "company": "Google",
                    "title": "Senior Engineer",
                    "start_date": "2020-01-01",
                    "end_date": "2023-01-01",
                },
            ],
            "educations": [
                {
                    "school": "MIT",
                    "degree": "BS",
                    "discipline": "Computer Science",
                },
            ],
            "experience_years": 5.0,
        }

    def test_all_filters_match(self) -> None:
        from greenhouse_mcp.harvest.sourcing import _matches_filters

        profile = self._make_profile()
        result = _matches_filters(
            profile,
            title_keywords=["engineer"],
            company_keywords=["google"],
            education_keywords=["MIT"],
            min_experience_years=3,
            tags=["Python"],
        )
        assert result is not None
        assert result["score"] == 5
        assert len(result["reasons"]) == 5

    def test_title_only(self) -> None:
        from greenhouse_mcp.harvest.sourcing import _matches_filters

        profile = self._make_profile()
        result = _matches_filters(
            profile, title_keywords=["engineer"]
        )
        assert result is not None
        assert result["score"] == 1
        assert "title:" in result["reasons"][0]

    def test_company_only(self) -> None:
        from greenhouse_mcp.harvest.sourcing import _matches_filters

        profile = self._make_profile()
        result = _matches_filters(
            profile, company_keywords=["google"]
        )
        assert result is not None
        assert result["score"] == 1

    def test_education_only(self) -> None:
        from greenhouse_mcp.harvest.sourcing import _matches_filters

        profile = self._make_profile()
        result = _matches_filters(
            profile, education_keywords=["computer science"]
        )
        assert result is not None
        assert result["score"] == 1

    def test_experience_only(self) -> None:
        from greenhouse_mcp.harvest.sourcing import _matches_filters

        profile = self._make_profile()
        result = _matches_filters(
            profile, min_experience_years=3
        )
        assert result is not None
        assert result["score"] == 1

    def test_tags_only(self) -> None:
        from greenhouse_mcp.harvest.sourcing import _matches_filters

        profile = self._make_profile()
        result = _matches_filters(profile, tags=["python"])
        assert result is not None
        assert result["score"] == 1

    def test_no_match_returns_none(self) -> None:
        from greenhouse_mcp.harvest.sourcing import _matches_filters

        profile = self._make_profile()
        result = _matches_filters(
            profile, title_keywords=["designer"]
        )
        assert result is None

    def test_no_filters_returns_all(self) -> None:
        from greenhouse_mcp.harvest.sourcing import _matches_filters

        profile = self._make_profile()
        result = _matches_filters(profile)
        assert result is not None
        assert result["score"] == 0
        assert result["reasons"] == ["no filters applied"]

    def test_partial_filter_mismatch_returns_none(self) -> None:
        from greenhouse_mcp.harvest.sourcing import _matches_filters

        profile = self._make_profile()
        # Title matches but company doesn't
        result = _matches_filters(
            profile,
            title_keywords=["engineer"],
            company_keywords=["facebook"],
        )
        assert result is None


# ─── search_pipeline_candidates ──────────────────────────────────────


def _mock_applications(candidate_ids: list[int]) -> list[dict]:
    """Create mock application objects."""
    return [
        {
            "id": 1000 + cid,
            "candidate_id": cid,
            "status": "active",
            "jobs": [{"id": 10, "name": "SWE"}],
        }
        for cid in candidate_ids
    ]


def _mock_candidates_for_sourcing() -> list[dict]:
    """Return candidate objects for sourcing tests."""
    return [
        {
            "id": 1,
            "first_name": "Alice",
            "last_name": "Smith",
            "title": "Senior Engineer",
            "company": "Google",
            "email_addresses": [
                {"value": "alice@example.com", "type": "personal"},
            ],
            "tags": [{"name": "Python"}],
            "employments": [
                {
                    "company_name": "Google",
                    "title": "Senior Engineer",
                    "start_date": "2020-01-01",
                    "end_date": "2023-01-01",
                },
            ],
            "educations": [
                {
                    "school_name": "MIT",
                    "degree": "BS",
                    "discipline": "CS",
                },
            ],
            "attachments": [],
        },
        {
            "id": 2,
            "first_name": "Bob",
            "last_name": "Jones",
            "title": "Product Manager",
            "company": "Meta",
            "email_addresses": [
                {"value": "bob@example.com", "type": "personal"},
            ],
            "tags": [],
            "employments": [
                {
                    "company_name": "Meta",
                    "title": "Product Manager",
                    "start_date": "2019-01-01",
                    "end_date": "2024-01-01",
                },
            ],
            "educations": [],
            "attachments": [],
        },
    ]


@respx.mock
@pytest.mark.asyncio
async def test_search_pipeline_finds_matches(
    client: GreenhouseClient,
) -> None:
    from greenhouse_mcp.harvest.sourcing import (
        search_pipeline_candidates,
    )

    # Mock applications for job 10
    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(
            200, json=_mock_applications([1, 2])
        )
    )
    # Mock candidates batch
    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(
            200, json=_mock_candidates_for_sourcing()
        )
    )

    result = await search_pipeline_candidates(
        client,
        job_ids=[10],
        title_keywords=["engineer"],
    )

    assert result["total_matched"] == 1
    assert result["total_scanned"] == 2
    matched = result["matched_candidates"]
    assert len(matched) == 1
    assert matched[0]["name"] == "Alice Smith"
    assert matched[0]["match_score"] == 1


@respx.mock
@pytest.mark.asyncio
async def test_search_pipeline_no_matches(
    client: GreenhouseClient,
) -> None:
    from greenhouse_mcp.harvest.sourcing import (
        search_pipeline_candidates,
    )

    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(
            200, json=_mock_applications([1, 2])
        )
    )
    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(
            200, json=_mock_candidates_for_sourcing()
        )
    )

    result = await search_pipeline_candidates(
        client,
        job_ids=[10],
        title_keywords=["designer"],
    )

    assert result["total_matched"] == 0
    assert result["matched_candidates"] == []


@respx.mock
@pytest.mark.asyncio
async def test_search_pipeline_api_error(
    client: GreenhouseClient,
) -> None:
    from greenhouse_mcp.harvest.sourcing import (
        search_pipeline_candidates,
    )

    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(
            500, json={"message": "Internal Server Error"}
        )
    )

    result = await search_pipeline_candidates(
        client,
        job_ids=[10],
        title_keywords=["engineer"],
    )

    assert result["total_matched"] == 0
    assert result["total_scanned"] == 0


@respx.mock
@pytest.mark.asyncio
async def test_search_pipeline_multiple_jobs(
    client: GreenhouseClient,
) -> None:
    from greenhouse_mcp.harvest.sourcing import (
        search_pipeline_candidates,
    )

    # Both jobs return the same candidates (deduplication test)
    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(
            200, json=_mock_applications([1, 2])
        )
    )
    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(
            200, json=_mock_candidates_for_sourcing()
        )
    )

    result = await search_pipeline_candidates(
        client,
        job_ids=[10, 20],
        title_keywords=["engineer"],
    )

    # Should still only find Alice once (dedup by candidate_id)
    assert result["total_matched"] == 1


@respx.mock
@pytest.mark.asyncio
async def test_search_pipeline_with_statuses(
    client: GreenhouseClient,
) -> None:
    from greenhouse_mcp.harvest.sourcing import (
        search_pipeline_candidates,
    )

    apps = [
        {
            "id": 1001,
            "candidate_id": 1,
            "status": "active",
            "jobs": [{"id": 10, "name": "SWE"}],
        },
        {
            "id": 1002,
            "candidate_id": 2,
            "status": "rejected",
            "jobs": [{"id": 10, "name": "SWE"}],
        },
    ]
    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=apps)
    )
    # Only Alice (active) should be batch-fetched
    alice = _mock_candidates_for_sourcing()[0]
    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=[alice])
    )

    # Only active — should exclude Bob (rejected)
    result = await search_pipeline_candidates(
        client,
        job_ids=[10],
        statuses=["active"],
    )

    assert result["total_scanned"] == 1
    assert result["total_matched"] == 1
    assert result["matched_candidates"][0]["name"] == "Alice Smith"


# ─── scan_all_candidates ─────────────────────────────────────────────


@respx.mock
@pytest.mark.asyncio
async def test_scan_basic(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.sourcing import scan_all_candidates

    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(
            200, json=_mock_candidates_for_sourcing()
        )
    )

    result = await scan_all_candidates(
        client, title_keywords=["engineer"]
    )

    assert result["total_scanned"] == 2
    assert result["total_matched"] == 1
    assert result["pages_fetched"] == 1
    assert result["matched_candidates"][0]["name"] == "Alice Smith"


@respx.mock
@pytest.mark.asyncio
async def test_scan_respects_max_pages(
    client: GreenhouseClient,
) -> None:
    from greenhouse_mcp.harvest.sourcing import scan_all_candidates

    call_count = 0

    def side_effect(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(
            200,
            json=_mock_candidates_for_sourcing(),
            headers={"link": '<https://next>; rel="next"'},
        )

    respx.get(f"{HARVEST_BASE}/candidates").mock(
        side_effect=side_effect
    )

    result = await scan_all_candidates(
        client, max_pages=2, title_keywords=["engineer"]
    )

    assert result["pages_fetched"] == 2
    assert call_count == 2


@respx.mock
@pytest.mark.asyncio
async def test_scan_respects_max_results(
    client: GreenhouseClient,
) -> None:
    from greenhouse_mcp.harvest.sourcing import scan_all_candidates

    # All candidates match (no filters), max_results=1
    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(
            200,
            json=_mock_candidates_for_sourcing(),
            headers={"link": '<https://next>; rel="next"'},
        )
    )

    result = await scan_all_candidates(client, max_results=1)

    assert result["total_matched"] == 1
    assert len(result["matched_candidates"]) == 1


@respx.mock
@pytest.mark.asyncio
async def test_scan_with_date_filter(
    client: GreenhouseClient,
) -> None:
    from greenhouse_mcp.harvest.sourcing import scan_all_candidates

    route = respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=[])
    )

    await scan_all_candidates(
        client, updated_after="2026-01-01"
    )

    request = route.calls[0].request
    assert "updated_after=2026-01-01" in str(request.url)


# ─── batch_read_resumes ──────────────────────────────────────────────


def _mock_candidate_with_resume() -> dict:
    return {
        "id": 1,
        "first_name": "Alice",
        "last_name": "Smith",
        "attachments": [
            {
                "type": "cover_letter",
                "filename": "cl.pdf",
                "url": "https://example.com/cl.pdf",
            },
            {
                "type": "resume",
                "filename": "resume.txt",
                "url": "https://example.com/resume.txt",
            },
        ],
    }


def _mock_candidate_no_resume() -> dict:
    return {
        "id": 2,
        "first_name": "Bob",
        "last_name": "Jones",
        "attachments": [
            {
                "type": "cover_letter",
                "filename": "cl.pdf",
                "url": "https://example.com/cl.pdf",
            },
        ],
    }


@respx.mock
@pytest.mark.asyncio
async def test_batch_read_basic(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.sourcing import batch_read_resumes

    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(
            200,
            json=[_mock_candidate_with_resume()],
        )
    )
    respx.get("https://example.com/resume.txt").mock(
        return_value=httpx.Response(
            200,
            text="Alice Smith\nSenior Engineer\nSkills: Python, Go",
            headers={"content-type": "text/plain"},
        )
    )

    result = await batch_read_resumes(
        client, candidate_ids=[1]
    )

    assert result["total_requested"] == 1
    assert result["total_with_resume"] == 1
    resumes = result["resumes"]
    assert len(resumes) == 1
    assert resumes[0]["candidate_id"] == 1
    assert resumes[0]["has_resume"] is True
    assert "Python" in resumes[0]["resume_text"]


@respx.mock
@pytest.mark.asyncio
async def test_batch_read_respects_max_candidates(
    client: GreenhouseClient,
) -> None:
    from greenhouse_mcp.harvest.sourcing import batch_read_resumes

    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=[])
    )

    result = await batch_read_resumes(
        client,
        candidate_ids=[1, 2, 3, 4, 5],
        max_candidates=2,
    )

    # Should only process 2 candidates
    assert result["total_requested"] == 2


@respx.mock
@pytest.mark.asyncio
async def test_batch_read_no_resume_attachment(
    client: GreenhouseClient,
) -> None:
    from greenhouse_mcp.harvest.sourcing import batch_read_resumes

    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(
            200,
            json=[_mock_candidate_no_resume()],
        )
    )

    result = await batch_read_resumes(
        client, candidate_ids=[2]
    )

    assert result["total_with_resume"] == 0
    resumes = result["resumes"]
    assert len(resumes) == 1
    assert resumes[0]["has_resume"] is False
    assert resumes[0]["resume_text"] is None


@respx.mock
@pytest.mark.asyncio
async def test_batch_read_download_error(
    client: GreenhouseClient,
) -> None:
    from greenhouse_mcp.harvest.sourcing import batch_read_resumes

    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(
            200,
            json=[_mock_candidate_with_resume()],
        )
    )
    respx.get("https://example.com/resume.txt").mock(
        return_value=httpx.Response(500)
    )

    result = await batch_read_resumes(
        client, candidate_ids=[1]
    )

    assert result["total_with_resume"] == 0
    resumes = result["resumes"]
    assert resumes[0]["has_resume"] is False
    assert resumes[0]["resume_text"] is None
