"""Tests for the composite workflow, analytics, batch and search tools (Harvest v3)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
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

    monkeypatch.setattr("greenhouse_mcp.harvest.batch.asyncio.sleep", _instant)


def _ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ids(request: httpx.Request, name: str = "ids") -> set[int]:
    raw = request.url.params.get(name, "")
    return {int(x) for x in raw.split(",") if x}


def _by_ids(rows: list[dict[str, Any]], key: str = "id", param: str = "ids"):  # type: ignore[no-untyped-def]
    def handler(request: httpx.Request) -> httpx.Response:
        wanted = _ids(request, param)
        return httpx.Response(200, json=[r for r in rows if r.get(key) in wanted])

    return handler


def _app(
    app_id: int,
    cid: int,
    *,
    stage: int | None = 901,
    stage_name: str = "Application Review",
    status: str = "in_process",
    job_id: int = 10,
    source_id: int | None = 1,
    created: str | None = None,
    last_activity: str | None = None,
) -> dict[str, Any]:
    return {
        "id": app_id,
        "candidate_id": cid,
        "job_id": job_id,
        "source_id": source_id,
        "status": status,
        "stage_id": app_id * 10,
        "job_interview_stage_id": stage,
        "stage_name": stage_name,
        "created_at": created or _ago(30),
        "last_activity_at": last_activity or _ago(1),
        "prospect": False,
    }


CANDIDATES = [
    {"id": 1, "first_name": "Alice", "last_name": "Smith"},
    {"id": 2, "first_name": "Bob", "last_name": "Jones"},
    {"id": 3, "first_name": "Carol", "last_name": "White"},
]
STAGES = [
    {"id": 902, "job_id": 10, "sort_order": 1, "name": "Phone Screen", "active": True},
    {"id": 901, "job_id": 10, "sort_order": 0, "name": "Application Review", "active": True},
    {"id": 903, "job_id": 10, "sort_order": 2, "name": "Onsite", "active": True},
    {"id": 899, "job_id": 10, "sort_order": 5, "name": "Retired", "active": False},
]


def _mock_lookups() -> dict[str, respx.Route]:
    return {
        "candidates": respx.get(f"{HARVEST_BASE}/candidates").mock(
            side_effect=_by_ids(CANDIDATES)
        ),
        "jobs": respx.get(f"{HARVEST_BASE}/jobs").mock(
            side_effect=_by_ids([{"id": 10, "name": "Backend Engineer"},
                                 {"id": 20, "name": "Designer"}])
        ),
        "sources": respx.get(f"{HARVEST_BASE}/sources").mock(
            side_effect=_by_ids([
                {"id": 1, "name": "LinkedIn", "type": {"id": 7, "name": "Prospecting"}},
                {"id": 2, "name": "Referral", "type": {"id": 8, "name": "Referral"}},
            ])
        ),
        "stages": respx.get(f"{HARVEST_BASE}/job_interview_stages").mock(
            return_value=httpx.Response(200, json=STAGES)
        ),
    }


# ─── pipeline_summary ────────────────────────────────────────────────


@respx.mock
@pytest.mark.asyncio
async def test_pipeline_summary_groups_by_stage_in_order(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.workflows import pipeline_summary

    routes = _mock_lookups()
    apps_route = respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=[
            _app(101, 1, stage=901),
            _app(102, 2, stage=902, stage_name="Phone Screen", source_id=2),
            _app(103, 3, stage=902, stage_name="Phone Screen", source_id=None,
                 last_activity=_ago(10)),
        ])
    )
    as_route = respx.get(f"{HARVEST_BASE}/application_stages").mock(
        return_value=httpx.Response(200, json=[
            {"id": 1, "application_id": 102, "job_interview_stage_id": 902,
             "entered_at": _ago(4), "exited_at": None, "days_in_stage": 4, "current": True},
        ])
    )

    result = await pipeline_summary(client, job_id=10)

    assert result["job_name"] == "Backend Engineer"
    assert result["total_active"] == 3
    names = [s["stage_name"] for s in result["stages"]]
    assert names == ["Application Review", "Phone Screen", "Onsite"]  # retired+empty dropped
    assert [s["count"] for s in result["stages"]] == [1, 2, 0]
    phone = {c["candidate_name"]: c for c in result["stages"][1]["candidates"]}
    assert phone["Bob Jones"]["source"] == "Referral"
    assert phone["Bob Jones"]["days_in_stage"] == 4
    assert phone["Carol White"]["source"] is None
    assert phone["Carol White"]["days_since_activity"] == 10
    assert phone["Carol White"]["days_in_stage"] is None

    params = apps_route.calls[0].request.url.params
    assert params["job_ids"] == "10" and params["status"] == "active"
    assert routes["stages"].calls[0].request.url.params["job_ids"] == "10"
    assert as_route.calls[0].request.url.params["current"] == "true"
    assert _ids(as_route.calls[0].request, "application_ids") == {101, 102, 103}
    assert _ids(routes["candidates"].calls[0].request) == {1, 2, 3}


@respx.mock
@pytest.mark.asyncio
async def test_pipeline_summary_job_not_found(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.workflows import pipeline_summary

    respx.get(f"{HARVEST_BASE}/jobs").mock(return_value=httpx.Response(200, json=[]))
    result = await pipeline_summary(client, job_id=999)
    assert result["status_code"] == 404


@respx.mock
@pytest.mark.asyncio
async def test_pipeline_summary_partial_on_application_error(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.workflows import pipeline_summary

    _mock_lookups()
    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(500, json={"message": "boom"})
    )
    result = await pipeline_summary(client, job_id=10)
    assert result["partial"] is True
    assert result["warnings"][0]["step"] == "fetch_applications"
    assert result["total_active"] == 0


# ─── stale_applications / candidates_needing_action ──────────────────


@respx.mock
@pytest.mark.asyncio
async def test_stale_applications_uses_server_side_filter(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.workflows import stale_applications

    _mock_lookups()
    apps_route = respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=[
            _app(101, 1, last_activity=_ago(20)),
            _app(102, 2, last_activity=_ago(40), stage_name="Onsite"),
            _app(103, 3, last_activity=_ago(30)),
        ])
    )
    result = await stale_applications(client, days=14, job_id=10, limit=2)

    params = apps_route.calls[0].request.url.params
    assert params["status"] == "active"
    assert params["job_ids"] == "10"
    cutoff = datetime.fromisoformat(params["last_activity_at[lte]"].replace("Z", "+00:00"))
    assert abs((datetime.now(timezone.utc) - cutoff).days - 14) <= 1

    assert result["total_stale"] == 3
    assert result["showing"] == 2
    top = result["stale_applications"][0]
    assert top["candidate_name"] == "Bob Jones"
    assert top["days_inactive"] == 40
    assert top["current_stage"] == "Onsite"
    assert top["job_name"] == "Backend Engineer"
    assert top["applied_at"] is not None


@respx.mock
@pytest.mark.asyncio
async def test_candidates_needing_action(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.workflows import candidates_needing_action

    _mock_lookups()
    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=[
            _app(101, 1, last_activity=_ago(2)),
            _app(102, 2, last_activity=_ago(9)),
        ])
    )
    iv_route = respx.get(f"{HARVEST_BASE}/interviews").mock(
        return_value=httpx.Response(200, json=[
            {"id": 70, "application_id": 101, "job_id": 10, "job_interview_id": 80,
             "status": "awaiting_feedback", "starts_at": "2026-04-01T10:00:00Z"},
            {"id": 71, "application_id": 102, "job_id": 10, "job_interview_id": 81,
             "status": "awaiting_feedback", "starts_at": "2026-04-02T10:00:00Z"},
        ])
    )
    respx.get(f"{HARVEST_BASE}/interviewers").mock(
        return_value=httpx.Response(200, json=[
            {"id": 1, "interview_id": 70, "user_id": 500, "scorecard_id": None,
             "email": "dana@example.com"},
            {"id": 2, "interview_id": 70, "user_id": 501, "scorecard_id": 9001,
             "email": "eve@example.com"},
            {"id": 3, "interview_id": 71, "user_id": 502, "scorecard_id": 9002,
             "email": "fay@example.com"},
        ])
    )
    respx.get(f"{HARVEST_BASE}/scorecards").mock(
        return_value=httpx.Response(200, json=[
            {"id": 9001, "status": "draft"}, {"id": 9002, "status": "complete"},
        ])
    )
    respx.get(f"{HARVEST_BASE}/users").mock(
        side_effect=_by_ids([
            {"id": 500, "first_name": "Dana", "last_name": "Lee"},
            {"id": 501, "first_name": None, "last_name": None, "primary_email": "eve@example.com"},
        ])
    )
    respx.get(f"{HARVEST_BASE}/job_interviews").mock(
        side_effect=_by_ids([{"id": 80, "name": "Technical Interview"}])
    )

    result = await candidates_needing_action(client, job_id=10, stale_days=7)

    assert result["total_active_reviewed"] == 2
    assert result["stale_count"] == 1
    assert result["stale_applications"][0]["candidate_name"] == "Bob Jones"
    assert result["missing_scorecard_count"] == 1
    missing = result["missing_scorecards"][0]
    assert missing["interview_id"] == 70
    assert missing["interview_name"] == "Technical Interview"
    assert missing["scheduled_at"] == "2026-04-01T10:00:00Z"
    assert missing["missing_scorecards_from"] == ["Dana Lee", "eve@example.com"]
    iv_params = iv_route.calls[0].request.url.params
    assert iv_params["status"] == "awaiting_feedback" and iv_params["job_ids"] == "10"


# ─── analytics ────────────────────────────────────────────────────────


@respx.mock
@pytest.mark.asyncio
async def test_pipeline_metrics_uses_stage_history(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.analytics import pipeline_metrics

    _mock_lookups()
    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=[
            _app(101, 1, stage=901),
            _app(102, 2, stage=902, stage_name="Phone Screen"),
            _app(103, 3, stage=902, status="rejected"),
            _app(104, 3, stage=903, status="hired"),
        ])
    )

    def row(app_id: int, stage: int, days: int, entered: bool = True) -> dict[str, Any]:
        return {"application_id": app_id, "job_interview_stage_id": stage,
                "entered_at": _ago(days) if entered else None, "days_in_stage": days}

    history = respx.get(f"{HARVEST_BASE}/application_stages").mock(
        return_value=httpx.Response(200, json=[
            row(101, 901, 2), row(101, 902, 0, entered=False),
            row(102, 901, 4), row(102, 902, 6),
            row(103, 901, 2), row(103, 902, 2),
            row(104, 901, 1), row(104, 902, 3), row(104, 903, 5),
            row(999, 901, 50),  # application on another job — ignored
        ])
    )

    result = await pipeline_metrics(client, job_id=10)

    assert _ids(history.calls[0].request, "job_interview_stage_ids") == {899, 901, 902, 903}
    assert result["total_applications"] == 4
    assert (result["active"], result["rejected"], result["hired"]) == (2, 1, 1)
    assert result["hire_rate_pct"] == 25.0
    assert result["reached_counts_from"] == "stage_history"
    stages = {s["stage_name"]: s for s in result["stages"]}
    assert list(stages) == ["Application Review", "Phone Screen", "Onsite"]
    assert stages["Application Review"]["total_reached"] == 4
    assert stages["Phone Screen"]["total_reached"] == 3
    assert stages["Onsite"]["total_reached"] == 1
    assert stages["Application Review"]["conversion_to_next_pct"] == 75.0
    assert stages["Phone Screen"]["conversion_to_next_pct"] == 33.3
    assert stages["Onsite"]["conversion_to_next_pct"] is None
    assert stages["Application Review"]["currently_active"] == 1
    assert stages["Phone Screen"]["currently_active"] == 1
    assert stages["Application Review"]["avg_days_in_stage"] == 2.2
    assert stages["Phone Screen"]["pct_of_total"] == 75.0


@respx.mock
@pytest.mark.asyncio
async def test_pipeline_metrics_falls_back_to_current_stage(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.analytics import pipeline_metrics

    _mock_lookups()
    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=[_app(101, 1, stage=901), _app(102, 2, stage=902)])
    )
    respx.get(f"{HARVEST_BASE}/application_stages").mock(
        return_value=httpx.Response(403, json={"message": "no scope"})
    )
    result = await pipeline_metrics(client, job_id=10)
    assert result["reached_counts_from"] == "current_stage_only"
    assert result["partial"] is True
    assert [s["total_reached"] for s in result["stages"]] == [1, 1, 0]


@respx.mock
@pytest.mark.asyncio
async def test_pipeline_metrics_no_applications(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.analytics import pipeline_metrics

    _mock_lookups()
    respx.get(f"{HARVEST_BASE}/applications").mock(return_value=httpx.Response(200, json=[]))
    result = await pipeline_metrics(client, job_id=10)
    assert result["total_applications"] == 0
    assert "message" in result


@respx.mock
@pytest.mark.asyncio
async def test_source_effectiveness(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.analytics import source_effectiveness

    routes = _mock_lookups()
    apps_route = respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=[
            _app(101, 1, source_id=1), _app(102, 2, source_id=1, status="hired"),
            _app(103, 3, source_id=1, status="rejected"), _app(104, 3, source_id=2),
            _app(105, 2, source_id=None),
        ])
    )
    result = await source_effectiveness(client, job_id=10, created_after="2026-01-01")

    params = apps_route.calls[0].request.url.params
    assert params["job_ids"] == "10"
    assert params["created_at[gt]"] == "2026-01-01T00:00:00Z"
    assert _ids(routes["sources"].calls[0].request) == {1, 2}
    assert result["total_applications"] == 5
    assert result["unique_sources"] == 3
    linkedin = result["sources"][0]
    assert linkedin["source"] == "LinkedIn"
    assert linkedin["strategy"] == "Prospecting"
    assert (linkedin["total"], linkedin["active"], linkedin["hired"], linkedin["rejected"]) == (
        3, 1, 1, 1
    )
    assert linkedin["hire_rate_pct"] == 33.3
    assert {s["source"] for s in result["sources"]} == {"LinkedIn", "Referral", "Unknown"}


@respx.mock
@pytest.mark.asyncio
async def test_time_to_hire_prefers_accepted_offer_date(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.analytics import time_to_hire

    _mock_lookups()
    apps_route = respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=[
            _app(101, 1, status="hired", created="2026-01-01T00:00:00Z",
                 last_activity="2026-03-01T00:00:00Z"),
            _app(102, 2, status="hired", created="2026-01-01T00:00:00Z",
                 last_activity="2026-01-21T00:00:00Z"),
        ])
    )
    offers_route = respx.get(f"{HARVEST_BASE}/offers").mock(
        return_value=httpx.Response(200, json=[
            {"id": 1, "application_id": 101, "status": "Accepted",
             "resolved_at": "2026-01-31T00:00:00Z"},
        ])
    )
    result = await time_to_hire(client, job_id=10)

    assert apps_route.calls[0].request.url.params["status"] == "hired"
    offer_params = offers_route.calls[0].request.url.params
    assert offer_params["status"] == "Accepted"
    assert _ids(offers_route.calls[0].request, "application_ids") == {101, 102}
    assert result["total_hires"] == 2
    assert result["min_days"] == 20 and result["max_days"] == 30
    assert result["avg_days_to_hire"] == 25.0
    hires = {h["candidate_name"]: h for h in result["recent_hires"]}
    assert hires["Alice Smith"]["hired_at_source"] == "accepted_offer"
    assert hires["Bob Jones"]["hired_at_source"] == "last_activity"
    assert hires["Alice Smith"]["job_name"] == "Backend Engineer"


@respx.mock
@pytest.mark.asyncio
async def test_time_to_hire_no_hires(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.analytics import time_to_hire

    respx.get(f"{HARVEST_BASE}/applications").mock(return_value=httpx.Response(200, json=[]))
    result = await time_to_hire(client)
    assert result["total_hires"] == 0


# ─── batch ────────────────────────────────────────────────────────────


@respx.mock
@pytest.mark.asyncio
async def test_bulk_reject_sends_v3_body(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.batch import bulk_reject

    ok = respx.post(f"{HARVEST_BASE}/applications/1/reject").mock(
        return_value=httpx.Response(204)
    )
    respx.post(f"{HARVEST_BASE}/applications/2/reject").mock(
        return_value=httpx.Response(422, json={"message": "already rejected"})
    )
    result = await bulk_reject(
        client,
        application_ids=[1, 2],
        rejection_reason_id=33,
        rejection_email=True,
        email_template_id=44,
        notes="Pipeline cleanup",
    )
    assert json.loads(ok.calls[0].request.content) == {
        "rejection_reason_id": 33,
        "notes": "Pipeline cleanup",
        "rejection_email": {"email_template_id": 44},
    }
    assert result["succeeded"] == 1 and result["failed"] == 1
    assert result["successful_ids"] == [1]
    assert result["failures"][0]["application_id"] == 2


@respx.mock
@pytest.mark.asyncio
async def test_bulk_reject_without_email(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.batch import bulk_reject

    route = respx.post(f"{HARVEST_BASE}/applications/1/reject").mock(
        return_value=httpx.Response(204)
    )
    await bulk_reject(client, application_ids=[1], rejection_reason_id=33)
    assert json.loads(route.calls[0].request.content) == {"rejection_reason_id": 33}


@pytest.mark.asyncio
async def test_bulk_reject_empty(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.batch import bulk_reject

    result = await bulk_reject(client, application_ids=[], rejection_reason_id=1)
    assert "error" in result


@respx.mock
@pytest.mark.asyncio
async def test_bulk_advance_moves_from_current_stage(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.batch import bulk_advance

    lookup = respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=[
            _app(1, 1, stage=901),
            _app(2, 2, stage=902, stage_name="Phone Screen"),
            _app(3, 3, stage=901, status="rejected"),
        ])
    )
    move1 = respx.post(f"{HARVEST_BASE}/applications/1/move").mock(
        return_value=httpx.Response(204)
    )
    move2 = respx.post(f"{HARVEST_BASE}/applications/2/move").mock(
        return_value=httpx.Response(204)
    )

    result = await bulk_advance(client, application_ids=[1, 2, 3, 4])

    assert _ids(lookup.calls[0].request) == {1, 2, 3, 4}
    assert json.loads(move1.calls[0].request.content) == {"from_stage_id": 901}
    assert json.loads(move2.calls[0].request.content) == {"from_stage_id": 902}
    assert result["succeeded"] == 2
    assert result["successful_ids"] == [1, 2]
    assert result["skipped"] == 1 and result["skipped_details"][0]["application_id"] == 3
    assert result["failed"] == 1 and result["failures"][0]["application_id"] == 4


@respx.mock
@pytest.mark.asyncio
async def test_bulk_advance_only_from_given_stage(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.batch import bulk_advance

    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=[
            _app(1, 1, stage=901), _app(2, 2, stage=902, stage_name="Phone Screen"),
        ])
    )
    move1 = respx.post(f"{HARVEST_BASE}/applications/1/move").mock(
        return_value=httpx.Response(204)
    )
    move2 = respx.post(f"{HARVEST_BASE}/applications/2/move").mock(
        return_value=httpx.Response(204)
    )
    result = await bulk_advance(client, application_ids=[1, 2], from_stage_id=902)
    assert not move1.called
    assert move2.called
    assert result["succeeded"] == 1 and result["skipped"] == 1


@respx.mock
@pytest.mark.asyncio
async def test_bulk_tag_existing_tag_skips_already_tagged(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.batch import bulk_tag

    respx.get(f"{HARVEST_BASE}/candidate_tags").mock(
        return_value=httpx.Response(200, json=[{"id": 5, "name": "Other"},
                                               {"id": 6, "name": "Hiring Event"}])
    )
    applied = respx.get(f"{HARVEST_BASE}/applied_candidate_tags").mock(
        return_value=httpx.Response(200, json=[
            {"id": 1, "candidate_id": 2, "candidate_tag_id": 6},
        ])
    )
    create_tag = respx.post(f"{HARVEST_BASE}/candidate_tags")
    apply = respx.post(f"{HARVEST_BASE}/applied_candidate_tags").mock(
        return_value=httpx.Response(201, json={"id": 99})
    )

    result = await bulk_tag(client, candidate_ids=[1, 2, 3], tag_name="hiring event")

    assert not create_tag.called
    assert applied.calls[0].request.url.params["candidate_tag_ids"] == "6"
    bodies = [json.loads(c.request.content) for c in apply.calls]
    assert bodies == [
        {"candidate_id": 1, "candidate_tag_id": 6},
        {"candidate_id": 3, "candidate_tag_id": 6},
    ]
    assert result["succeeded"] == 2
    assert result["already_tagged_ids"] == [2]
    assert result["tag_id"] == 6 and result["tag_created"] is False


@respx.mock
@pytest.mark.asyncio
async def test_bulk_tag_creates_missing_tag(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.batch import bulk_tag

    respx.get(f"{HARVEST_BASE}/candidate_tags").mock(return_value=httpx.Response(200, json=[]))
    create_tag = respx.post(f"{HARVEST_BASE}/candidate_tags").mock(
        return_value=httpx.Response(201, json={"id": 77, "name": "New Tag"})
    )
    apply = respx.post(f"{HARVEST_BASE}/applied_candidate_tags").mock(
        return_value=httpx.Response(201, json={"id": 1})
    )
    result = await bulk_tag(client, candidate_ids=[1], tag_name="New Tag")
    assert json.loads(create_tag.calls[0].request.content) == {"name": "New Tag"}
    assert json.loads(apply.calls[0].request.content) == {"candidate_id": 1,
                                                          "candidate_tag_id": 77}
    assert result["tag_created"] is True and result["succeeded"] == 1


@pytest.mark.asyncio
async def test_bulk_tag_empty(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.batch import bulk_tag

    assert "error" in await bulk_tag(client, candidate_ids=[], tag_name="x")


def test_batch_tools_are_detected_as_writes() -> None:
    from greenhouse_mcp.harvest import batch
    from greenhouse_mcp.server import _is_write_tool

    for fn in (batch.bulk_reject, batch.bulk_advance, batch.bulk_tag):
        assert _is_write_tool(fn)


def test_read_tools_are_not_detected_as_writes() -> None:
    from greenhouse_mcp.harvest import analytics, screening, search, sourcing, workflows
    from greenhouse_mcp.server import _is_write_tool

    for module in (analytics, screening, search, sourcing, workflows):
        for name in dir(module):
            fn = getattr(module, name)
            if (
                callable(fn)
                and not name.startswith("_")
                and getattr(fn, "__module__", "") == module.__name__
            ):
                assert not _is_write_tool(fn), name


# ─── search ───────────────────────────────────────────────────────────


@respx.mock
@pytest.mark.asyncio
async def test_search_by_name_scans_pages_with_cursor(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.search import search_candidates_by_name

    seen: list[dict[str, str]] = []
    pages = [
        [{"id": 1, "first_name": "Sarah", "last_name": "Chen"},
         {"id": 2, "first_name": "Tom", "last_name": "Hardy"}],
        [{"id": 3, "first_name": "Sam", "last_name": "O'Sarah"},
         {"id": 4, "first_name": "Alexandra", "last_name": "Diaz", "preferred_name": "Sarah"}],
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(dict(request.url.params))
        n = len(seen)
        headers = (
            {"link": f'<{HARVEST_BASE}/candidates?cursor=c{n + 1}>; rel="next"'}
            if n < len(pages)
            else {}
        )
        return httpx.Response(200, json=pages[n - 1], headers=headers)

    respx.get(f"{HARVEST_BASE}/candidates").mock(side_effect=handler)
    result = await search_candidates_by_name(client, name="sarah", per_page=2)

    assert seen[0] == {"per_page": "2"}
    assert seen[1] == {"cursor": "c2"}
    assert [m["id"] for m in result["matches"]] == [1, 3, 4]
    assert result["pages_scanned"] == 2
    assert result["has_more"] is False and result["next_cursor"] is None


@respx.mock
@pytest.mark.asyncio
async def test_search_by_name_reports_more_pages(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.search import search_candidates_by_name

    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(
            200,
            json=[{"id": 1, "first_name": "Ann", "last_name": "Lee"}],
            headers={"link": f'<{HARVEST_BASE}/candidates?cursor=next1>; rel="next"'},
        )
    )
    result = await search_candidates_by_name(client, name="zed", max_pages=1)
    assert result["total_matches"] == 0
    assert result["has_more"] is True
    assert result["next_cursor"] == "next1"


@respx.mock
@pytest.mark.asyncio
async def test_search_by_name_resumes_from_cursor(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.search import search_candidates_by_name

    route = respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=[])
    )
    await search_candidates_by_name(client, name="x", cursor="abc")
    assert dict(route.calls[0].request.url.params) == {"cursor": "abc"}


@respx.mock
@pytest.mark.asyncio
async def test_search_by_name_error(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.search import search_candidates_by_name

    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(403, json={"message": "nope"})
    )
    result = await search_candidates_by_name(client, name="x")
    assert result["status_code"] == 403


@respx.mock
@pytest.mark.asyncio
async def test_search_by_email(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.search import search_candidates_by_email

    route = respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "first_name": "Ann"}])
    )
    result = await search_candidates_by_email(client, email="ann@example.com")
    assert route.calls[0].request.url.params["email"] == "ann@example.com"
    assert result["items"][0]["id"] == 1
