"""Tests for harvest/sourcing.py — composite sourcing tools (Harvest v3)."""
from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx

from greenhouse_mcp.client import GreenhouseClient

HARVEST_BASE = "https://harvest.greenhouse.io/v3"


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _instant(_seconds: float) -> None:
        return None

    monkeypatch.setattr("greenhouse_mcp.harvest.sourcing.asyncio.sleep", _instant)


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

    def test_negative_date_range_ignored(self) -> None:
        from greenhouse_mcp.harvest.sourcing import (
            _calculate_experience_years,
        )

        # end_date before start_date (data entry error) — should be ignored
        result = _calculate_experience_years([
            {
                "start_date": "2023-01-01",
                "end_date": "2020-01-01",
            }
        ])
        assert result is None


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


# ─── _matches_whole_word ─────────────────────────────────────────────


class TestMatchesWholeWord:
    def test_basic_match(self) -> None:
        from greenhouse_mcp.harvest.sourcing import _matches_whole_word

        result = _matches_whole_word("Java developer with Spring", ["Java"])
        assert result == ["Java"]

    def test_no_substring_match(self) -> None:
        from greenhouse_mcp.harvest.sourcing import _matches_whole_word

        result = _matches_whole_word("JavaScript and TypeScript developer", ["Java"])
        assert result == []

    def test_case_insensitive(self) -> None:
        from greenhouse_mcp.harvest.sourcing import _matches_whole_word

        result = _matches_whole_word("Expert in JAVA and Python", ["java"])
        assert result == ["java"]

    def test_special_chars_in_keyword(self) -> None:
        from greenhouse_mcp.harvest.sourcing import _matches_whole_word

        result = _matches_whole_word("C++ and Python developer", ["C++"])
        assert result == ["C++"]

    def test_multiple_keywords(self) -> None:
        from greenhouse_mcp.harvest.sourcing import _matches_whole_word

        result = _matches_whole_word(
            "Java developer who also uses Go and JavaScript",
            ["Java", "Go", "Rust"],
        )
        assert "Java" in result
        assert "Go" in result
        assert "Rust" not in result

    def test_empty_inputs(self) -> None:
        from greenhouse_mcp.harvest.sourcing import _matches_whole_word

        assert _matches_whole_word("", ["Java"]) == []
        assert _matches_whole_word("some text", []) == []

    def test_keyword_at_boundaries(self) -> None:
        from greenhouse_mcp.harvest.sourcing import _matches_whole_word

        # At start of string
        assert _matches_whole_word("Java is great", ["Java"]) == ["Java"]
        # At end of string
        assert _matches_whole_word("I know Java", ["Java"]) == ["Java"]
        # With punctuation
        assert _matches_whole_word("Java, Python, and Go", ["Java"]) == ["Java"]
        # With parentheses
        assert _matches_whole_word("languages (Java)", ["Java"]) == ["Java"]


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
            "tags": ["Python", "Senior"],
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


# ─── v3 mock helpers ─────────────────────────────────────────────────


def _ids(request: httpx.Request, name: str) -> set[int]:
    raw = request.url.params.get(name, "")
    return {int(x) for x in raw.split(",") if x}


def _app(app_id: int, cid: int, job_id: int = 10, status: str = "in_process") -> dict[str, Any]:
    return {"id": app_id, "candidate_id": cid, "job_id": job_id, "status": status}


def _cand(cid: int, name: str, **extra: Any) -> dict[str, Any]:
    first, _, last = name.partition(" ")
    return {
        "id": cid,
        "first_name": first,
        "last_name": last,
        "title": None,
        "company": None,
        "tags": [],
        "email_addresses": [],
        **extra,
    }


def _resume(cid: int, *, att_id: int | None = None, created: str = "2026-01-01T00:00:00Z",
            url: str | None = None) -> dict[str, Any]:
    return {
        "id": att_id or cid * 10,
        "application_id": cid * 100,
        "candidate_id": cid,
        "type": "resume",
        "filename": f"resume_{cid}.txt",
        "url": url or f"https://example.com/resume_{cid}.txt",
        "created_at": created,
    }


def _mock_v3(
    *,
    apps: list[dict[str, Any]] | None = None,
    candidates: list[dict[str, Any]] | None = None,
    attachments: list[dict[str, Any]] | None = None,
    employments: list[dict[str, Any]] | None = None,
    educations: list[dict[str, Any]] | None = None,
    options: list[dict[str, Any]] | None = None,
) -> dict[str, respx.Route]:
    """Mock the v3 list endpoints, honouring the id filters the tools send."""
    apps = apps or []
    candidates = candidates or []

    def applications(request: httpx.Request) -> httpx.Response:
        jobs = _ids(request, "job_ids")
        status = request.url.params.get("status")
        rows = [
            a for a in apps
            if (not jobs or a.get("job_id") in jobs)
            and (status is None or {"active": "in_process"}.get(status, status) == a["status"])
        ]
        return httpx.Response(200, json=rows)

    def by_ids(rows: list[dict[str, Any]], key: str, param: str):  # type: ignore[no-untyped-def]
        def handler(request: httpx.Request) -> httpx.Response:
            wanted = _ids(request, param)
            return httpx.Response(200, json=[r for r in rows if r.get(key) in wanted])
        return handler

    return {
        "applications": respx.get(f"{HARVEST_BASE}/applications").mock(side_effect=applications),
        "candidates": respx.get(f"{HARVEST_BASE}/candidates").mock(
            side_effect=by_ids(candidates, "id", "ids")
        ),
        "attachments": respx.get(f"{HARVEST_BASE}/attachments").mock(
            side_effect=by_ids(attachments or [], "candidate_id", "candidate_ids")
        ),
        "employments": respx.get(f"{HARVEST_BASE}/candidate_employments").mock(
            side_effect=by_ids(employments or [], "candidate_id", "candidate_ids")
        ),
        "educations": respx.get(f"{HARVEST_BASE}/candidate_educations").mock(
            side_effect=by_ids(educations or [], "candidate_id", "candidate_ids")
        ),
        "options": respx.get(f"{HARVEST_BASE}/custom_field_options").mock(
            side_effect=by_ids(options or [], "id", "ids")
        ),
    }


def _sourcing_people() -> dict[str, list[dict[str, Any]]]:
    """Alice (engineer at Google, MIT) and Bob (PM at Meta)."""
    return {
        "candidates": [
            _cand(1, "Alice Smith", title="Senior Engineer", company="Google",
                  tags=["Python"], email_addresses=[{"value": "alice@example.com",
                                                     "type": "personal"}]),
            _cand(2, "Bob Jones", title="Product Manager", company="Meta"),
        ],
        "employments": [
            {"id": 11, "candidate_id": 1, "company_name": "Google", "title": "Senior Engineer",
             "start_date": "2018-01-01", "end_date": None, "latest": True},
            {"id": 21, "candidate_id": 2, "company_name": "Meta", "title": "Product Manager",
             "start_date": "2020-01-01", "end_date": "2024-01-01", "latest": True},
        ],
        "educations": [
            {"id": 31, "candidate_id": 1, "school_name_custom_field_option_id": 501,
             "degree_custom_field_option_id": 502, "discipline_custom_field_option_id": 503,
             "start_at": "2010-09-01T00:00:00Z", "end_at": "2014-06-01T00:00:00Z"},
        ],
        "options": [
            {"id": 501, "name": "MIT"},
            {"id": 502, "name": "BS"},
            {"id": 503, "name": "Computer Science"},
        ],
    }


# ─── _enrich_candidates ──────────────────────────────────────────────


@respx.mock
@pytest.mark.asyncio
async def test_enrich_attaches_employments_and_named_educations(
    client: GreenhouseClient,
) -> None:
    from greenhouse_mcp.harvest.sourcing import _build_candidate_profile, _enrich_candidates

    people = _sourcing_people()
    routes = _mock_v3(**people)
    cands = [dict(c) for c in people["candidates"]]
    await _enrich_candidates(client, cands)

    alice = _build_candidate_profile(cands[0])
    assert alice["employments"][0] == {
        "company": "Google", "title": "Senior Engineer", "start_date": "2018-01-01",
        "end_date": None,
    }
    assert alice["educations"] == [
        {"school": "MIT", "degree": "BS", "discipline": "Computer Science"}
    ]
    assert alice["experience_years"] is not None and alice["experience_years"] > 8
    assert alice["tags"] == ["Python"]
    assert _build_candidate_profile(cands[1])["educations"] == []
    assert _ids(routes["employments"].calls[0].request, "candidate_ids") == {1, 2}
    assert _ids(routes["options"].calls[0].request, "ids") == {501, 502, 503}

    # Already-enriched candidates aren't fetched again
    await _enrich_candidates(client, cands)
    assert routes["employments"].call_count == 1
    assert routes["educations"].call_count == 1


# ─── search_pipeline_candidates ──────────────────────────────────────


@respx.mock
@pytest.mark.asyncio
async def test_search_pipeline_finds_matches(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.sourcing import search_pipeline_candidates

    routes = _mock_v3(apps=[_app(1001, 1), _app(1002, 2)], **_sourcing_people())
    result = await search_pipeline_candidates(client, job_ids=[10], title_keywords=["engineer"])

    assert result["total_scanned"] == 2
    assert result["total_matched"] == 1
    match = result["matched_candidates"][0]
    assert match["name"] == "Alice Smith"
    assert match["match_score"] == 2  # title scores 2
    assert match["email"] == "alice@example.com"
    # Final results are fully enriched even though only employments were needed to filter
    assert match["educations"][0]["school"] == "MIT"
    assert routes["applications"].calls[0].request.url.params["job_ids"] == "10"
    assert _ids(routes["candidates"].calls[0].request, "ids") == {1, 2}


@respx.mock
@pytest.mark.asyncio
async def test_search_pipeline_education_filter(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.sourcing import search_pipeline_candidates

    _mock_v3(apps=[_app(1001, 1), _app(1002, 2)], **_sourcing_people())
    result = await search_pipeline_candidates(
        client, job_ids=[10], education_keywords=["mit"], company_keywords=["google"]
    )
    # Bob has company data that doesn't match → excluded
    assert [m["name"] for m in result["matched_candidates"]] == ["Alice Smith"]
    alice = result["matched_candidates"][0]
    assert alice["match_score"] == 2
    assert "education: mit" in alice["match_reasons"]


@respx.mock
@pytest.mark.asyncio
async def test_search_pipeline_no_matches(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.sourcing import search_pipeline_candidates

    _mock_v3(apps=[_app(1001, 1), _app(1002, 2)], **_sourcing_people())
    result = await search_pipeline_candidates(client, job_ids=[10], title_keywords=["designer"])
    assert result["total_matched"] == 0
    assert result["matched_candidates"] == []


@respx.mock
@pytest.mark.asyncio
async def test_search_pipeline_api_error(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.sourcing import search_pipeline_candidates

    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(500, json={"message": "Internal Server Error"})
    )
    result = await search_pipeline_candidates(client, job_ids=[10], title_keywords=["engineer"])
    assert result["total_matched"] == 0
    assert result["total_scanned"] == 0


@respx.mock
@pytest.mark.asyncio
async def test_search_pipeline_multiple_jobs_single_request(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.sourcing import search_pipeline_candidates

    routes = _mock_v3(
        apps=[_app(1001, 1, job_id=10), _app(1002, 2, job_id=20), _app(1003, 1, job_id=20)],
        **_sourcing_people(),
    )
    result = await search_pipeline_candidates(
        client, job_ids=[10, 20], title_keywords=["engineer"]
    )
    assert result["total_scanned"] == 2
    assert result["total_matched"] == 1
    assert routes["applications"].call_count == 1
    assert routes["applications"].calls[0].request.url.params["job_ids"] == "10,20"


@respx.mock
@pytest.mark.asyncio
async def test_search_pipeline_with_statuses(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.sourcing import search_pipeline_candidates

    routes = _mock_v3(
        apps=[_app(1001, 1), _app(1002, 2, status="rejected")], **_sourcing_people()
    )
    result = await search_pipeline_candidates(
        client, job_ids=[10], statuses=["active"], title_keywords=["engineer"]
    )
    assert routes["applications"].calls[0].request.url.params["status"] == "active"
    assert result["total_scanned"] == 1
    assert result["total_matched"] == 1
    assert result["matched_candidates"][0]["name"] == "Alice Smith"


@respx.mock
@pytest.mark.asyncio
async def test_search_pipeline_tags_only_skips_profile_fetch_for_filtering(
    client: GreenhouseClient,
) -> None:
    from greenhouse_mcp.harvest.sourcing import search_pipeline_candidates

    routes = _mock_v3(apps=[_app(1001, 1), _app(1002, 2)], **_sourcing_people())
    result = await search_pipeline_candidates(client, job_ids=[10], tags=["python"])
    names = [m["name"] for m in result["matched_candidates"]]
    assert names[0] == "Alice Smith"
    # employments fetched once, only for the final result set
    assert routes["employments"].call_count == 1
    assert _ids(routes["employments"].calls[0].request, "candidate_ids") == set(
        m["id"] for m in result["matched_candidates"]
    )


# ─── scan_all_candidates ─────────────────────────────────────────────


@respx.mock
@pytest.mark.asyncio
async def test_scan_basic(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.sourcing import scan_all_candidates

    people = _sourcing_people()
    _mock_v3(**people)
    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=people["candidates"])
    )
    result = await scan_all_candidates(client, title_keywords=["engineer"])
    assert result["total_scanned"] == 2
    assert result["total_matched"] == 1
    assert result["pages_fetched"] == 1
    assert result["matched_candidates"][0]["name"] == "Alice Smith"


@respx.mock
@pytest.mark.asyncio
async def test_scan_follows_cursor_and_respects_max_pages(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.sourcing import scan_all_candidates

    people = _sourcing_people()
    _mock_v3(**people)
    seen: list[dict[str, str]] = []

    def pages(request: httpx.Request) -> httpx.Response:
        seen.append(dict(request.url.params))
        n = len(seen)
        return httpx.Response(
            200,
            json=people["candidates"],
            headers={"link": f'<{HARVEST_BASE}/candidates?cursor=page{n + 1}>; rel="next"'},
        )

    respx.get(f"{HARVEST_BASE}/candidates").mock(side_effect=pages)
    result = await scan_all_candidates(client, max_pages=2, title_keywords=["engineer"])
    assert result["pages_fetched"] == 2
    assert len(seen) == 2
    assert seen[0]["per_page"] == "500"
    assert seen[1] == {"cursor": "page2"}  # v3: cursor requests carry no other params


@respx.mock
@pytest.mark.asyncio
async def test_scan_respects_max_results(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.sourcing import scan_all_candidates

    people = _sourcing_people()
    _mock_v3(**people)
    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=people["candidates"])
    )
    result = await scan_all_candidates(client, max_results=1)
    assert result["total_matched"] == 1
    assert len(result["matched_candidates"]) == 1


@respx.mock
@pytest.mark.asyncio
async def test_scan_with_date_filter(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.sourcing import scan_all_candidates

    route = respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=[])
    )
    await scan_all_candidates(client, updated_after="2026-01-01")
    params = route.calls[0].request.url.params
    assert params["updated_at[gt]"] == "2026-01-01T00:00:00Z"
    assert "updated_after" not in params


# ─── batch_read_resumes ──────────────────────────────────────────────


def _text(url: str, body: str, status: int = 200) -> None:
    respx.get(url).mock(
        return_value=httpx.Response(status, text=body, headers={"content-type": "text/plain"})
    )


@respx.mock
@pytest.mark.asyncio
async def test_batch_read_basic_uses_latest_resume(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.sourcing import batch_read_resumes

    routes = _mock_v3(
        candidates=[_cand(1, "Jane Doe")],
        attachments=[
            _resume(1, att_id=1, created="2024-01-01T00:00:00Z",
                    url="https://example.com/old.txt"),
            _resume(1, att_id=2, created="2026-01-01T00:00:00Z",
                    url="https://example.com/new.txt"),
        ],
    )
    _text("https://example.com/new.txt", "Senior Python engineer")
    result = await batch_read_resumes(client, candidate_ids=[1])

    assert result["total_requested"] == 1
    assert result["total_with_resume"] == 1
    resume = result["resumes"][0]
    assert resume["candidate_id"] == 1
    assert resume["candidate_name"] == "Jane Doe"
    assert resume["has_resume"] is True
    assert "Python" in resume["resume_text"]
    att_params = routes["attachments"].calls[0].request.url.params
    assert att_params["candidate_ids"] == "1" and att_params["type"] == "resume"


@respx.mock
@pytest.mark.asyncio
async def test_batch_read_respects_max_candidates(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.sourcing import batch_read_resumes

    routes = _mock_v3()
    result = await batch_read_resumes(client, candidate_ids=[1, 2, 3, 4], max_candidates=2)
    assert result["total_requested"] == 2
    assert _ids(routes["candidates"].calls[0].request, "ids") == {1, 2}


@respx.mock
@pytest.mark.asyncio
async def test_batch_read_no_resume_attachment(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.sourcing import batch_read_resumes

    cover = {**_resume(1), "type": "cover_letter"}
    _mock_v3(candidates=[_cand(1, "Jane Doe")], attachments=[cover])
    result = await batch_read_resumes(client, candidate_ids=[1])
    assert result["total_with_resume"] == 0
    assert result["resumes"][0]["has_resume"] is False
    assert result["resumes"][0]["resume_text"] is None


@respx.mock
@pytest.mark.asyncio
async def test_batch_read_download_error(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.sourcing import batch_read_resumes

    _mock_v3(candidates=[_cand(1, "Jane Doe")], attachments=[_resume(1)])
    _text("https://example.com/resume_1.txt", "gone", status=403)
    result = await batch_read_resumes(client, candidate_ids=[1])
    assert result["total_with_resume"] == 0
    assert result["resumes"][0]["has_resume"] is False
    assert result["resumes"][0]["resume_text"] is None
    assert result["resumes"][0]["resume_filename"] == "resume_1.txt"


@respx.mock
@pytest.mark.asyncio
async def test_batch_read_candidate_not_found(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.sourcing import batch_read_resumes

    _mock_v3()
    result = await batch_read_resumes(client, candidate_ids=[999])
    assert result["total_requested"] == 1
    assert result["total_with_resume"] == 0
    assert result["resumes"][0]["candidate_id"] == 999
    assert result["resumes"][0]["has_resume"] is False
    assert result["resumes"][0]["candidate_name"] == "999"


# ─── scan_pipeline_resumes ──────────────────────────────────────────


async def _scan(
    client: GreenhouseClient, people: list[tuple[int, str, str]], **kwargs: Any
) -> dict[str, Any]:
    """Set up a job-10 pipeline whose candidates have the given resume texts, then scan."""
    from greenhouse_mcp.harvest.sourcing import scan_pipeline_resumes

    _mock_v3(
        apps=[_app(1000 + cid, cid) for cid, _, _ in people],
        candidates=[_cand(cid, name) for cid, name, _ in people],
        attachments=[_resume(cid) for cid, _, _ in people],
    )
    for cid, _, text in people:
        _text(f"https://example.com/resume_{cid}.txt", text)
    return await scan_pipeline_resumes(client, job_ids=[10], **kwargs)


@respx.mock
@pytest.mark.asyncio
async def test_scan_pipeline_resumes_empty_pipeline(client: GreenhouseClient) -> None:
    result = await _scan(client, [], keywords=["Python"])
    assert result["total_in_pipeline"] == 0
    assert result["resumes_scanned"] == 0
    assert result["total_matched"] == 0
    assert result["matched_candidates"] == []
    assert "search_diagnostics" in result


@respx.mock
@pytest.mark.asyncio
async def test_scan_pipeline_resumes_basic(client: GreenhouseClient) -> None:
    result = await _scan(
        client,
        [(1, "Alice Smith", "Expert in OCaml and C++ with Haskell experience"),
         (2, "Bob Jones", "Java developer with Spring Boot and microservices")],
        keywords=["OCaml", "C++", "Haskell"],
    )
    assert result["total_in_pipeline"] == 2
    assert result["resumes_scanned"] == 2
    assert result["total_matched"] == 1
    match = result["matched_candidates"][0]
    assert match["candidate_name"] == "Alice Smith"
    assert match["resume_filename"] == "resume_1.txt"
    assert {"OCaml", "C++"} <= set(match["matched_keywords"])
    assert len(match["keyword_snippets"]) >= 1


@respx.mock
@pytest.mark.asyncio
async def test_scan_pipeline_resumes_no_matches(client: GreenhouseClient) -> None:
    result = await _scan(
        client, [(1, "Bob Jones", "Java developer with Spring Boot")], keywords=["OCaml", "Rust"]
    )
    assert result["total_matched"] == 0
    assert result["resumes_scanned"] == 1


@respx.mock
@pytest.mark.asyncio
async def test_scan_pipeline_resumes_respects_max(client: GreenhouseClient) -> None:
    result = await _scan(
        client,
        [(1, "A B", "OCaml developer"), (2, "C D", "OCaml developer"),
         (3, "E F", "OCaml developer")],
        keywords=["OCaml"],
        max_resumes=1,
    )
    assert result["resumes_scanned"] == 1


@respx.mock
@pytest.mark.asyncio
async def test_scan_pipeline_resumes_skips_candidates_without_resume(
    client: GreenhouseClient,
) -> None:
    from greenhouse_mcp.harvest.sourcing import scan_pipeline_resumes

    routes = _mock_v3(
        apps=[_app(1001, 1), _app(1002, 2)],
        candidates=[_cand(1, "Alice Smith"), _cand(2, "Bob Jones")],
        attachments=[_resume(2)],
    )
    _text("https://example.com/resume_2.txt", "Python developer")
    result = await scan_pipeline_resumes(client, job_ids=[10], keywords=["Python"])
    assert result["resumes_scanned"] == 1
    assert result["matched_candidates"][0]["candidate_name"] == "Bob Jones"
    # names are only fetched for candidates that have a resume
    assert _ids(routes["candidates"].calls[0].request, "ids") == {2}


@respx.mock
@pytest.mark.asyncio
async def test_scan_pipeline_resumes_sorts_by_keyword_count(client: GreenhouseClient) -> None:
    result = await _scan(
        client,
        [(1, "A B", "I know Python and nothing else"),
         (2, "C D", "Expert in Python, OCaml, and Haskell")],
        keywords=["Python", "OCaml", "Haskell"],
    )
    matched = result["matched_candidates"]
    assert result["total_matched"] == 2
    assert matched[0]["candidate_name"] == "C D" and len(matched[0]["matched_keywords"]) == 3
    assert matched[1]["candidate_name"] == "A B" and len(matched[1]["matched_keywords"]) == 1


@pytest.mark.parametrize(
    ("people", "kwargs", "expected"),
    [
        pytest.param(
            [(1, "Alice Smith", "Expert in OCaml and C++ with systems experience"),
             (2, "Bob Jones", "OCaml developer with Haskell background")],
            {"required_keywords": ["OCaml", "C++"]},
            ["Alice Smith"],
            id="required_gate",
        ),
        pytest.param(
            [(1, "Alice Smith", "Python and Java developer with Spring Boot"),
             (2, "Bob Jones", "Python developer with Django and Flask")],
            {"keywords": ["Python"], "exclude_keywords": ["Java"]},
            ["Bob Jones"],
            id="exclude",
        ),
        pytest.param(
            [(1, "Alice Smith", "OCaml and JavaScript developer with React"),
             (2, "Bob Jones", "OCaml developer, previously used Java and Spring")],
            {"required_keywords": ["OCaml"], "exclude_keywords": ["Java"]},
            ["Alice Smith"],
            id="exclude_word_boundary",
        ),
        pytest.param(
            [(1, "Alice Smith", "OCaml expert, also skilled in C++ and Rust"),
             (2, "Bob Jones", "OCaml and Haskell developer, previously Java"),
             (3, "Carol White", "OCaml developer with some Rust experience")],
            {"required_keywords": ["OCaml"], "keywords": ["C++", "Rust", "Haskell"],
             "exclude_keywords": ["Java"]},
            ["Alice Smith", "Carol White"],
            id="boolean_combined",
        ),
    ],
)
@respx.mock
@pytest.mark.asyncio
async def test_scan_pipeline_resumes_boolean_logic(
    client: GreenhouseClient,
    people: list[tuple[int, str, str]],
    kwargs: dict[str, Any],
    expected: list[str],
) -> None:
    result = await _scan(client, people, **kwargs)
    assert [m["candidate_name"] for m in result["matched_candidates"]] == expected
    assert result["total_matched"] == len(expected)


@respx.mock
@pytest.mark.asyncio
async def test_scan_pipeline_resumes_keywords_still_works_alone(
    client: GreenhouseClient,
) -> None:
    result = await _scan(
        client, [(1, "Alice Smith", "Python and Django developer")],
        keywords=["Python", "Django", "Flask"],
    )
    kws = result["matched_candidates"][0]["matched_keywords"]
    assert "Python" in kws and "Django" in kws and "Flask" not in kws


@pytest.mark.asyncio
async def test_scan_pipeline_resumes_no_keywords_raises(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.sourcing import scan_pipeline_resumes

    with pytest.raises(ValueError):
        await scan_pipeline_resumes(client, job_ids=[10])


@respx.mock
@pytest.mark.asyncio
async def test_scan_pipeline_resumes_diagnostics_keyword_frequency(
    client: GreenhouseClient,
) -> None:
    result = await _scan(
        client,
        [(1, "Alice Smith", "Expert in Python and Django"),
         (2, "Bob Jones", "Python developer with Flask")],
        keywords=["Python", "Django", "Flask"],
    )
    freq = result["search_diagnostics"]["keyword_frequency"]
    assert freq == {"Python": 2, "Django": 1, "Flask": 1}


@respx.mock
@pytest.mark.asyncio
async def test_scan_pipeline_resumes_diagnostics_exclude_tracking(
    client: GreenhouseClient,
) -> None:
    result = await _scan(
        client,
        [(1, "Alice Smith", "Python and Java developer"),
         (2, "Bob Jones", "Python developer with Django")],
        keywords=["Python"],
        exclude_keywords=["Java"],
    )
    diag = result["search_diagnostics"]
    assert diag["excluded_count"] == 1
    assert diag["excluded_by"] == {"Java": 1}
    assert result["total_matched"] == 1


@respx.mock
@pytest.mark.asyncio
async def test_scan_pipeline_resumes_diagnostics_near_misses(
    client: GreenhouseClient,
) -> None:
    result = await _scan(
        client,
        [(1, "Alice Smith", "Expert in OCaml and C++ systems programming"),
         (2, "Bob Jones", "OCaml developer with Haskell experience")],
        required_keywords=["OCaml", "C++"],
        keywords=["Haskell"],
    )
    assert result["total_matched"] == 1
    diag = result["search_diagnostics"]
    assert diag["required_failed_count"] == 1
    near_miss = diag["near_misses"][0]
    assert near_miss["candidate_name"] == "Bob Jones"
    assert near_miss["matched_required"] == ["OCaml"]
    assert near_miss["missing_required"] == ["C++"]
    assert near_miss["matched_keywords"] == ["Haskell"]


@respx.mock
@pytest.mark.asyncio
async def test_scan_pipeline_resumes_status_filter(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.sourcing import scan_pipeline_resumes

    routes = _mock_v3(
        apps=[_app(1001, 1, status="rejected"), _app(1002, 2)],
        candidates=[_cand(1, "Alice Smith"), _cand(2, "Bob Jones")],
        attachments=[_resume(1), _resume(2)],
    )
    _text("https://example.com/resume_1.txt", "Python")
    _text("https://example.com/resume_2.txt", "Python")
    result = await scan_pipeline_resumes(
        client, job_ids=[10], keywords=["Python"], statuses=["rejected", "hired"]
    )
    assert result["total_in_pipeline"] == 1
    assert [m["candidate_name"] for m in result["matched_candidates"]] == ["Alice Smith"]
    statuses = {c.request.url.params["status"] for c in routes["applications"].calls}
    assert statuses == {"rejected", "hired"}
