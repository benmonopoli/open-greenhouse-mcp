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
        assert result["score"] == 6  # title=2 + company + edu + exp + tags
        assert len(result["reasons"]) == 5

    def test_title_only(self) -> None:
        from greenhouse_mcp.harvest.sourcing import _matches_filters

        profile = self._make_profile()
        result = _matches_filters(
            profile, title_keywords=["engineer"]
        )
        assert result is not None
        assert result["score"] == 2  # title scores 2
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
    assert matched[0]["match_score"] == 2  # title scores 2


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


# ─── _extract_keyword_snippets ──────────────────────────────────────


class TestExtractKeywordSnippets:
    def test_basic_snippet(self) -> None:
        from greenhouse_mcp.harvest.sourcing import (
            _extract_keyword_snippets,
        )

        text = "I have 5 years of experience with OCaml and Haskell."
        result = _extract_keyword_snippets(text, ["OCaml"])
        assert len(result) == 1
        assert result[0]["keyword"] == "OCaml"
        assert "OCaml" in result[0]["snippet"]

    def test_multiple_keywords(self) -> None:
        from greenhouse_mcp.harvest.sourcing import (
            _extract_keyword_snippets,
        )

        text = "Expert in Python, C++, and distributed systems."
        result = _extract_keyword_snippets(
            text, ["Python", "C++", "Rust"]
        )
        assert len(result) == 2  # Rust not found
        keywords_found = [r["keyword"] for r in result]
        assert "Python" in keywords_found
        assert "C++" in keywords_found

    def test_empty_inputs(self) -> None:
        from greenhouse_mcp.harvest.sourcing import (
            _extract_keyword_snippets,
        )

        assert _extract_keyword_snippets("", ["test"]) == []
        assert _extract_keyword_snippets("text", []) == []

    def test_deduplication(self) -> None:
        from greenhouse_mcp.harvest.sourcing import (
            _extract_keyword_snippets,
        )

        text = "OCaml OCaml OCaml everywhere"
        result = _extract_keyword_snippets(text, ["OCaml", "ocaml"])
        # Same keyword (case-insensitive) should appear only once
        assert len(result) == 1


# ─── _matches_filters soft logic ────────────────────────────────────


class TestMatchesFiltersSoft:
    """Test the soft-match behavior for sparse candidate data."""

    def _make_sparse_profile(self) -> dict:
        """Candidate with no structured data — typical Greenhouse profile."""
        return {
            "id": 99,
            "name": "Sparse Candidate",
            "title": "",
            "company": "",
            "email": None,
            "tags": [],
            "employments": [],
            "educations": [],
            "experience_years": None,
        }

    def test_sparse_with_title_filter_passes(self) -> None:
        from greenhouse_mcp.harvest.sourcing import _matches_filters

        profile = self._make_sparse_profile()
        result = _matches_filters(
            profile, title_keywords=["engineer"]
        )
        # No title data → skip filter, don't reject
        assert result is not None
        assert result["score"] == 0
        assert "needs resume review" in result["reasons"][0]

    def test_sparse_with_experience_filter_passes(self) -> None:
        from greenhouse_mcp.harvest.sourcing import _matches_filters

        profile = self._make_sparse_profile()
        result = _matches_filters(
            profile, min_experience_years=5
        )
        # No employment dates → skip filter, don't reject
        assert result is not None
        assert result["score"] == 0

    def test_sparse_with_all_filters_passes(self) -> None:
        from greenhouse_mcp.harvest.sourcing import _matches_filters

        profile = self._make_sparse_profile()
        result = _matches_filters(
            profile,
            title_keywords=["engineer"],
            company_keywords=["google"],
            min_experience_years=5,
            tags=["Python"],
        )
        # All data absent → all filters skipped → passes with score 0
        assert result is not None
        assert result["score"] == 0

    def test_wrong_title_still_rejects(self) -> None:
        from greenhouse_mcp.harvest.sourcing import _matches_filters

        profile = self._make_sparse_profile()
        profile["title"] = "Product Manager"
        result = _matches_filters(
            profile, title_keywords=["engineer"]
        )
        # Has title data that doesn't match → reject
        assert result is None


# ─── scan_pipeline_resumes ──────────────────────────────────────────


def _mock_candidate_with_text_resume(
    cid: int, name: str, resume_text: str
) -> dict:
    return {
        "id": cid,
        "first_name": name.split()[0] if " " in name else name,
        "last_name": name.split()[-1] if " " in name else "",
        "title": "",
        "company": "",
        "tags": [],
        "employments": [],
        "educations": [],
        "attachments": [
            {
                "type": "resume",
                "filename": "resume.txt",
                "url": f"https://example.com/resume_{cid}.txt",
            },
        ],
    }


@respx.mock
@pytest.mark.asyncio
async def test_scan_pipeline_resumes_basic(
    client: GreenhouseClient,
) -> None:
    from greenhouse_mcp.harvest.sourcing import scan_pipeline_resumes

    apps = [
        {"id": 1001, "candidate_id": 1, "status": "active",
         "jobs": [{"id": 10}]},
        {"id": 1002, "candidate_id": 2, "status": "active",
         "jobs": [{"id": 10}]},
    ]
    cand1 = _mock_candidate_with_text_resume(
        1, "Alice Smith", "Expert in OCaml and C++ with Haskell"
    )
    cand2 = _mock_candidate_with_text_resume(
        2, "Bob Jones", "Java developer with Spring Boot"
    )

    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=apps)
    )
    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=[cand1, cand2])
    )
    respx.get("https://example.com/resume_1.txt").mock(
        return_value=httpx.Response(
            200,
            text="Expert in OCaml and C++ with Haskell experience",
            headers={"content-type": "text/plain"},
        )
    )
    respx.get("https://example.com/resume_2.txt").mock(
        return_value=httpx.Response(
            200,
            text="Java developer with Spring Boot and microservices",
            headers={"content-type": "text/plain"},
        )
    )

    result = await scan_pipeline_resumes(
        client,
        job_ids=[10],
        keywords=["OCaml", "C++", "Haskell"],
    )

    assert result["total_in_pipeline"] == 2
    assert result["resumes_scanned"] == 2
    assert result["total_matched"] == 1
    matched = result["matched_candidates"]
    assert len(matched) == 1
    assert matched[0]["candidate_name"] == "Alice Smith"
    assert "OCaml" in matched[0]["matched_keywords"]
    assert "C++" in matched[0]["matched_keywords"]
    assert len(matched[0]["keyword_snippets"]) >= 1


@respx.mock
@pytest.mark.asyncio
async def test_scan_pipeline_resumes_no_matches(
    client: GreenhouseClient,
) -> None:
    from greenhouse_mcp.harvest.sourcing import scan_pipeline_resumes

    apps = [
        {"id": 1001, "candidate_id": 1, "status": "active",
         "jobs": [{"id": 10}]},
    ]
    cand1 = _mock_candidate_with_text_resume(
        1, "Alice Smith", "Java developer"
    )

    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=apps)
    )
    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=[cand1])
    )
    respx.get("https://example.com/resume_1.txt").mock(
        return_value=httpx.Response(
            200,
            text="Java developer with Spring Boot",
            headers={"content-type": "text/plain"},
        )
    )

    result = await scan_pipeline_resumes(
        client,
        job_ids=[10],
        keywords=["OCaml", "Rust"],
    )

    assert result["total_matched"] == 0
    assert result["resumes_scanned"] == 1


@respx.mock
@pytest.mark.asyncio
async def test_scan_pipeline_resumes_respects_max(
    client: GreenhouseClient,
) -> None:
    from greenhouse_mcp.harvest.sourcing import scan_pipeline_resumes

    # 3 candidates but max_resumes=1
    apps = [
        {"id": 1001, "candidate_id": 1, "status": "active",
         "jobs": [{"id": 10}]},
        {"id": 1002, "candidate_id": 2, "status": "active",
         "jobs": [{"id": 10}]},
        {"id": 1003, "candidate_id": 3, "status": "active",
         "jobs": [{"id": 10}]},
    ]
    cands = [
        _mock_candidate_with_text_resume(1, "A B", "OCaml dev"),
        _mock_candidate_with_text_resume(2, "C D", "OCaml dev"),
        _mock_candidate_with_text_resume(3, "E F", "OCaml dev"),
    ]

    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=apps)
    )
    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=cands)
    )
    respx.get("https://example.com/resume_1.txt").mock(
        return_value=httpx.Response(
            200, text="OCaml developer",
            headers={"content-type": "text/plain"},
        )
    )

    result = await scan_pipeline_resumes(
        client,
        job_ids=[10],
        keywords=["OCaml"],
        max_resumes=1,
    )

    assert result["resumes_scanned"] == 1


@respx.mock
@pytest.mark.asyncio
async def test_scan_pipeline_resumes_sorts_by_keyword_count(
    client: GreenhouseClient,
) -> None:
    from greenhouse_mcp.harvest.sourcing import scan_pipeline_resumes

    apps = [
        {"id": 1001, "candidate_id": 1, "status": "active",
         "jobs": [{"id": 10}]},
        {"id": 1002, "candidate_id": 2, "status": "active",
         "jobs": [{"id": 10}]},
    ]
    # Candidate 1: matches 1 keyword, Candidate 2: matches 3
    cand1 = _mock_candidate_with_text_resume(1, "A B", "")
    cand2 = _mock_candidate_with_text_resume(2, "C D", "")

    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=apps)
    )
    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=[cand1, cand2])
    )
    respx.get("https://example.com/resume_1.txt").mock(
        return_value=httpx.Response(
            200, text="I know Python and nothing else",
            headers={"content-type": "text/plain"},
        )
    )
    respx.get("https://example.com/resume_2.txt").mock(
        return_value=httpx.Response(
            200, text="Expert in Python, OCaml, and Haskell",
            headers={"content-type": "text/plain"},
        )
    )

    result = await scan_pipeline_resumes(
        client,
        job_ids=[10],
        keywords=["Python", "OCaml", "Haskell"],
    )

    assert result["total_matched"] == 2
    matched = result["matched_candidates"]
    # C D should rank first (3 matches vs 1)
    assert matched[0]["candidate_name"] == "C D"
    assert len(matched[0]["matched_keywords"]) == 3
    assert matched[1]["candidate_name"] == "A B"
    assert len(matched[1]["matched_keywords"]) == 1


@respx.mock
@pytest.mark.asyncio
async def test_scan_pipeline_resumes_required_keywords_gate(
    client: GreenhouseClient,
) -> None:
    """Required keywords act as AND gate — all must be present."""
    from greenhouse_mcp.harvest.sourcing import scan_pipeline_resumes

    apps = [
        {"id": 1001, "candidate_id": 1, "status": "active",
         "jobs": [{"id": 10}]},
        {"id": 1002, "candidate_id": 2, "status": "active",
         "jobs": [{"id": 10}]},
    ]
    cand1 = _mock_candidate_with_text_resume(1, "Alice Smith", "")
    cand2 = _mock_candidate_with_text_resume(2, "Bob Jones", "")

    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=apps)
    )
    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=[cand1, cand2])
    )
    respx.get("https://example.com/resume_1.txt").mock(
        return_value=httpx.Response(
            200, text="Expert in OCaml and C++ with systems experience",
            headers={"content-type": "text/plain"},
        )
    )
    respx.get("https://example.com/resume_2.txt").mock(
        return_value=httpx.Response(
            200, text="OCaml developer with Haskell background",
            headers={"content-type": "text/plain"},
        )
    )

    result = await scan_pipeline_resumes(
        client,
        job_ids=[10],
        required_keywords=["OCaml", "C++"],
    )

    assert result["total_matched"] == 1
    matched = result["matched_candidates"]
    assert matched[0]["candidate_name"] == "Alice Smith"
    assert "OCaml" in matched[0]["matched_keywords"]
    assert "C++" in matched[0]["matched_keywords"]


@respx.mock
@pytest.mark.asyncio
async def test_scan_pipeline_resumes_exclude_keywords(
    client: GreenhouseClient,
) -> None:
    """Exclude keywords disqualify candidates."""
    from greenhouse_mcp.harvest.sourcing import scan_pipeline_resumes

    apps = [
        {"id": 1001, "candidate_id": 1, "status": "active",
         "jobs": [{"id": 10}]},
        {"id": 1002, "candidate_id": 2, "status": "active",
         "jobs": [{"id": 10}]},
    ]
    cand1 = _mock_candidate_with_text_resume(1, "Alice Smith", "")
    cand2 = _mock_candidate_with_text_resume(2, "Bob Jones", "")

    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=apps)
    )
    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=[cand1, cand2])
    )
    respx.get("https://example.com/resume_1.txt").mock(
        return_value=httpx.Response(
            200, text="Python and Java developer with Spring Boot",
            headers={"content-type": "text/plain"},
        )
    )
    respx.get("https://example.com/resume_2.txt").mock(
        return_value=httpx.Response(
            200, text="Python developer with Django and Flask",
            headers={"content-type": "text/plain"},
        )
    )

    result = await scan_pipeline_resumes(
        client,
        job_ids=[10],
        keywords=["Python"],
        exclude_keywords=["Java"],
    )

    assert result["total_matched"] == 1
    matched = result["matched_candidates"]
    assert matched[0]["candidate_name"] == "Bob Jones"


@respx.mock
@pytest.mark.asyncio
async def test_scan_pipeline_resumes_boolean_combined(
    client: GreenhouseClient,
) -> None:
    """Combined: required gate + keywords ranking + exclude filter."""
    from greenhouse_mcp.harvest.sourcing import scan_pipeline_resumes

    apps = [
        {"id": 1001, "candidate_id": 1, "status": "active",
         "jobs": [{"id": 10}]},
        {"id": 1002, "candidate_id": 2, "status": "active",
         "jobs": [{"id": 10}]},
        {"id": 1003, "candidate_id": 3, "status": "active",
         "jobs": [{"id": 10}]},
    ]
    cand1 = _mock_candidate_with_text_resume(1, "Alice Smith", "")
    cand2 = _mock_candidate_with_text_resume(2, "Bob Jones", "")
    cand3 = _mock_candidate_with_text_resume(3, "Carol White", "")

    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=apps)
    )
    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=[cand1, cand2, cand3])
    )
    respx.get("https://example.com/resume_1.txt").mock(
        return_value=httpx.Response(
            200, text="OCaml expert, also skilled in C++ and Rust",
            headers={"content-type": "text/plain"},
        )
    )
    respx.get("https://example.com/resume_2.txt").mock(
        return_value=httpx.Response(
            200, text="OCaml and Haskell developer, previously Java",
            headers={"content-type": "text/plain"},
        )
    )
    respx.get("https://example.com/resume_3.txt").mock(
        return_value=httpx.Response(
            200, text="OCaml developer with some Rust experience",
            headers={"content-type": "text/plain"},
        )
    )

    result = await scan_pipeline_resumes(
        client,
        job_ids=[10],
        required_keywords=["OCaml"],
        keywords=["C++", "Rust", "Haskell"],
        exclude_keywords=["Java"],
    )

    assert result["total_matched"] == 2  # Bob excluded (Java)
    matched = result["matched_candidates"]
    # Alice ranks first (2 preferred: C++, Rust) over Carol (1 preferred: Rust)
    assert matched[0]["candidate_name"] == "Alice Smith"
    assert matched[1]["candidate_name"] == "Carol White"


@respx.mock
@pytest.mark.asyncio
async def test_scan_pipeline_resumes_keywords_still_works_alone(
    client: GreenhouseClient,
) -> None:
    """Plain keywords param still works exactly as before (backward compat)."""
    from greenhouse_mcp.harvest.sourcing import scan_pipeline_resumes

    apps = [
        {"id": 1001, "candidate_id": 1, "status": "active",
         "jobs": [{"id": 10}]},
    ]
    cand1 = _mock_candidate_with_text_resume(1, "Alice Smith", "")

    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=apps)
    )
    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=[cand1])
    )
    respx.get("https://example.com/resume_1.txt").mock(
        return_value=httpx.Response(
            200, text="Python and Django developer",
            headers={"content-type": "text/plain"},
        )
    )

    result = await scan_pipeline_resumes(
        client,
        job_ids=[10],
        keywords=["Python", "Django", "Flask"],
    )

    assert result["total_matched"] == 1
    matched = result["matched_candidates"]
    assert "Python" in matched[0]["matched_keywords"]
    assert "Django" in matched[0]["matched_keywords"]
    assert "Flask" not in matched[0]["matched_keywords"]


@respx.mock
@pytest.mark.asyncio
async def test_scan_pipeline_resumes_no_keywords_raises(
    client: GreenhouseClient,
) -> None:
    """Must provide at least keywords or required_keywords."""
    from greenhouse_mcp.harvest.sourcing import scan_pipeline_resumes

    with pytest.raises(ValueError, match="keywords.*required_keywords"):
        await scan_pipeline_resumes(
            client,
            job_ids=[10],
        )
