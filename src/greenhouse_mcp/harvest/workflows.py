"""Harvest API — Composite workflow tools (3 tools).

High-level tools that combine multiple API calls into single operations
that match how recruiters actually think about their work.

Harvest v3 no longer embeds related records (job names, stage names, sources,
interviewers), so these tools resolve them with batched id lookups
(``harvest_get_ids``) instead of per-record calls. The private helpers here
are shared by the other composite modules (screening, analytics, sourcing,
batch).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient

# ─── Shared private helpers ──────────────────────────────────────────


def _is_error(result: Any) -> bool:
    return GreenhouseClient._is_error(result)


def _person_name(record: dict[str, Any]) -> str:
    first = record.get("first_name") or ""
    last = record.get("last_name") or ""
    return f"{first} {last}".strip()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _days_since(value: str | None, now: datetime) -> int | None:
    dt = _parse_dt(value)
    return (now - dt).days if dt else None


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _to_datetime(value: str) -> str:
    """Normalise a user-supplied date for v3 date filters, which require ISO 8601
    date-times: ``2026-04-14`` → ``2026-04-14T00:00:00Z``."""
    value = value.strip()
    if len(value) == 10 and value[4] == "-" and value[7] == "-":
        return f"{value}T00:00:00Z"
    return value


def _simple_status(status: str | None) -> str:
    """Map a v3 application status to the filter vocabulary.

    v3 records read ``in_process`` for active applications, while the status
    filter (and recruiters) say ``active``.
    """
    return "active" if status == "in_process" else (status or "")


async def _resolve_names(
    client: GreenhouseClient,
    endpoint: str,
    ids: set[int] | list[int],
    params: dict[str, Any] | None = None,
) -> dict[Any, str]:
    """Batch-fetch ``{id: name}`` for records with a ``name`` field (jobs, sources,
    rejection reasons, job interviews, custom field options...). Best effort:
    returns what it could resolve."""
    wanted = {i for i in ids if i is not None}
    if not wanted:
        return {}
    query = {"per_page": 100, **(params or {})}
    result = await client.harvest_get_ids(endpoint, "ids", sorted(wanted), params=query)
    if _is_error(result):
        return {}
    return {r["id"]: r.get("name") or "" for r in result.get("items", []) if "id" in r}


async def _resolve_candidate_names(
    client: GreenhouseClient,
    candidate_ids: set[int],
) -> dict[Any, str]:
    """Batch-fetch candidate names by ID (50 ids per request). Returns {id: "First Last"}."""
    wanted = {i for i in candidate_ids if i is not None}
    if not wanted:
        return {}
    result = await client.harvest_get_ids(
        "/candidates",
        "ids",
        sorted(wanted),
        params={"per_page": 100, "fields": ["id", "first_name", "last_name"]},
    )
    if _is_error(result):
        return {}
    return {c["id"]: _person_name(c) for c in result.get("items", []) if "id" in c}


async def _resolve_user_names(client: GreenhouseClient, user_ids: set[int]) -> dict[Any, str]:
    wanted = {i for i in user_ids if i is not None}
    if not wanted:
        return {}
    result = await client.harvest_get_ids(
        "/users", "ids", sorted(wanted), params={"per_page": 100}
    )
    if _is_error(result):
        return {}
    return {
        u["id"]: _person_name(u) or u.get("primary_email") or str(u["id"])
        for u in result.get("items", [])
        if "id" in u
    }


async def _job_stages(client: GreenhouseClient, job_ids: list[int]) -> list[dict[str, Any]]:
    """Interview stages for jobs, ordered by job then pipeline position (sort_order)."""
    result = await client.harvest_get_ids(
        "/job_interview_stages", "job_ids", job_ids, params={"per_page": 500}
    )
    if _is_error(result):
        return []
    stages = list(result.get("items", []))
    stages.sort(key=lambda s: (s.get("job_id") or 0, s.get("sort_order") or 0))
    return stages


async def _fetch_applications(
    client: GreenhouseClient,
    params: dict[str, Any],
    step: str = "fetch_applications",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Fetch every application matching params. Returns (applications, warnings)."""
    query = {"per_page": 500, **params}
    result = await client.harvest_get("/applications", params=query, paginate="all")
    if _is_error(result):
        return [], [{"step": step, **result}]
    warnings: list[dict[str, Any]] = []
    if result.get("partial"):
        warnings.append({"step": step, "partial": True, **(result.get("error") or {})})
    return list(result.get("items", [])), warnings


def _with_warnings(data: dict[str, Any], warnings: list[dict[str, Any]]) -> dict[str, Any]:
    if warnings:
        data["warnings"] = warnings
        data["partial"] = True
    return data


# ─── Public tools ─────────────────────────────────────────────────────


async def pipeline_summary(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID — list_jobs → match by name")],
) -> dict[str, Any]:
    """Complete pipeline view for a job — candidates grouped by stage. Read-only.

    Users say "show me the pipeline for Backend Engineer" or "how many
    candidates are in each stage." To find the job_id: list_jobs → match by
    name. Returns the job's interview stages in pipeline order, each with its
    active candidates: names, source, days in the current stage, and days since
    last activity. One call replaces 5-10 sequential API calls.
    """
    now = datetime.now(timezone.utc)

    job = await client.harvest_get_by_id("/jobs", job_id)
    if _is_error(job):
        return job  # Can't continue without the job

    stages_list = await _job_stages(client, [job_id])
    all_apps, warnings = await _fetch_applications(
        client, {"job_ids": [job_id], "status": "active"}
    )

    app_ids = [a["id"] for a in all_apps if a.get("id") is not None]
    cand_ids = {a["candidate_id"] for a in all_apps if a.get("candidate_id")}
    source_ids = {a["source_id"] for a in all_apps if a.get("source_id")}

    names = await _resolve_candidate_names(client, cand_ids)
    sources = await _resolve_names(client, "/sources", source_ids)

    # Time in the current stage comes from the application's current stage entry.
    entered: dict[Any, dict[str, Any]] = {}
    if app_ids:
        stage_rows = await client.harvest_get_ids(
            "/application_stages",
            "application_ids",
            app_ids,
            params={"current": True, "per_page": 500},
        )
        if _is_error(stage_rows):
            warnings.append({"step": "fetch_application_stages", **stage_rows})
        else:
            for row in stage_rows.get("items", []):
                entered[row.get("application_id")] = row

    grouped: dict[Any, list[dict[str, Any]]] = {}
    stage_names_seen: dict[Any, str] = {}
    for app in all_apps:
        key = app.get("job_interview_stage_id") or app.get("stage_name") or "Unknown"
        stage_names_seen.setdefault(key, app.get("stage_name") or "Unknown")
        cid = app.get("candidate_id")
        current = entered.get(app.get("id")) or {}
        days_in_stage = current.get("days_in_stage")
        if days_in_stage is None:
            days_in_stage = _days_since(current.get("entered_at"), now)
        grouped.setdefault(key, []).append(
            {
                "application_id": app.get("id"),
                "candidate_id": cid,
                "candidate_name": names.get(cid, str(cid)) if cid else "",
                "applied_at": app.get("created_at"),
                "entered_stage_at": current.get("entered_at"),
                "days_in_stage": days_in_stage,
                "last_activity": app.get("last_activity_at"),
                "days_since_activity": _days_since(app.get("last_activity_at"), now),
                "source": sources.get(app.get("source_id")) if app.get("source_id") else None,
            }
        )

    ordered_stages: list[dict[str, Any]] = []
    for stage in stages_list:
        candidates = grouped.pop(stage["id"], [])
        if not stage.get("active", True) and not candidates:
            continue  # retired stage with nobody in it
        ordered_stages.append(
            {
                "stage_name": stage.get("name"),
                "stage_id": stage["id"],
                "count": len(candidates),
                "candidates": candidates,
            }
        )
    # Any stage not in the job's interview plan (shouldn't normally happen)
    for key, candidates in grouped.items():
        ordered_stages.append(
            {
                "stage_name": stage_names_seen.get(key, "Unknown"),
                "count": len(candidates),
                "candidates": candidates,
            }
        )

    return _with_warnings(
        {
            "job_id": job_id,
            "job_name": job.get("name"),
            "total_active": len(all_apps),
            "stages": ordered_stages,
        },
        warnings,
    )


async def _stale_rows(
    client: GreenhouseClient,
    stale_raw: list[tuple[dict[str, Any], int]],
) -> list[dict[str, Any]]:
    """Shape stale (application, days_inactive) pairs with candidate and job names."""
    names = await _resolve_candidate_names(
        client, {a["candidate_id"] for a, _ in stale_raw if a.get("candidate_id")}
    )
    jobs = await _resolve_names(
        client, "/jobs", {a["job_id"] for a, _ in stale_raw if a.get("job_id")}
    )
    rows: list[dict[str, Any]] = []
    for app, days_inactive in stale_raw:
        cid = app.get("candidate_id")
        rows.append(
            {
                "application_id": app.get("id"),
                "candidate_id": cid,
                "candidate_name": names.get(cid, str(cid)) if cid else "",
                "current_stage": app.get("stage_name"),
                "job_interview_stage_id": app.get("job_interview_stage_id"),
                "job_id": app.get("job_id"),
                "job_name": jobs.get(app["job_id"]) if app.get("job_id") else None,
                "last_activity": app.get("last_activity_at"),
                "days_inactive": days_inactive,
                "applied_at": app.get("created_at"),
            }
        )
    return rows


async def candidates_needing_action(
    client: GreenhouseClient,
    *,
    job_id: Annotated[
        int | None, Field(description="Filter to one job — list_jobs → match by name")
    ] = None,
    stale_days: Annotated[int, Field(description="Days without activity to flag as stale")] = 7,
) -> dict[str, Any]:
    """Find candidates that need attention — stale apps, missing scorecards. Read-only.

    Users say "what needs my attention?" or "who's been sitting too long?"
    Pass job_id for one job (list_jobs → match by name) or omit for all
    active applications. Returns stale applications sorted by urgency and
    interviews awaiting feedback, with the interviewers whose scorecards are
    still missing.
    """
    now = datetime.now(timezone.utc)

    params: dict[str, Any] = {"status": "active"}
    if job_id:
        params["job_ids"] = [job_id]
    all_apps, warnings = await _fetch_applications(client, params)

    stale_raw: list[tuple[dict[str, Any], int]] = []
    for app in all_apps:
        days_inactive = _days_since(app.get("last_activity_at"), now)
        if days_inactive is not None and days_inactive >= stale_days:
            stale_raw.append((app, days_inactive))
    stale_raw.sort(key=lambda x: x[1], reverse=True)
    stale = await _stale_rows(client, stale_raw)

    # Interviews that are over but still waiting on scorecards
    needs_scorecard: list[dict[str, Any]] = []
    iv_params: dict[str, Any] = {"status": "awaiting_feedback", "per_page": 100}
    if job_id:
        iv_params["job_ids"] = [job_id]
    interviews_result = await client.harvest_get("/interviews", params=iv_params)
    if _is_error(interviews_result):
        warnings.append({"step": "fetch_interviews", **interviews_result})
    else:
        interviews = interviews_result.get("items", [])
        iv_ids = [iv["id"] for iv in interviews if iv.get("id") is not None]
        panel: dict[Any, list[dict[str, Any]]] = {}
        scorecard_status: dict[int, str] = {}
        if iv_ids:
            panel_result = await client.harvest_get_ids(
                "/interviewers", "interview_ids", iv_ids, params={"per_page": 500}
            )
            if _is_error(panel_result):
                warnings.append({"step": "fetch_interviewers", **panel_result})
            else:
                for row in panel_result.get("items", []):
                    panel.setdefault(row.get("interview_id"), []).append(row)
            sc_ids = {
                r["scorecard_id"] for rows in panel.values() for r in rows if r.get("scorecard_id")
            }
            if sc_ids:
                sc_result = await client.harvest_get_ids(
                    "/scorecards",
                    "ids",
                    sorted(sc_ids),
                    params={"per_page": 100, "fields": ["id", "status"]},
                )
                if not _is_error(sc_result):
                    scorecard_status = {
                        s["id"]: s.get("status", "") for s in sc_result.get("items", [])
                    }

        missing_by_iv: dict[Any, list[dict[str, Any]]] = {}
        for iv_id, rows in panel.items():
            missing = [
                r
                for r in rows
                if not r.get("scorecard_id")
                or scorecard_status.get(r["scorecard_id"], "complete") != "complete"
            ]
            if missing:
                missing_by_iv[iv_id] = missing

        users = await _resolve_user_names(
            client,
            {r["user_id"] for rows in missing_by_iv.values() for r in rows if r.get("user_id")},
        )
        iv_names = await _resolve_names(
            client,
            "/job_interviews",
            {iv["job_interview_id"] for iv in interviews if iv.get("job_interview_id")},
        )
        for interview in interviews:
            missing = missing_by_iv.get(interview.get("id"), [])
            if not missing:
                continue
            needs_scorecard.append(
                {
                    "interview_id": interview.get("id"),
                    "application_id": interview.get("application_id"),
                    "job_id": interview.get("job_id"),
                    "interview_name": iv_names.get(interview.get("job_interview_id")),
                    "scheduled_at": interview.get("starts_at")
                    or interview.get("all_day_start_on"),
                    "missing_scorecards_from": [
                        users.get(r.get("user_id")) or r.get("email") or str(r.get("user_id"))
                        for r in missing
                    ],
                }
            )

    return _with_warnings(
        {
            "stale_applications": stale,
            "stale_count": len(stale),
            "missing_scorecards": needs_scorecard,
            "missing_scorecard_count": len(needs_scorecard),
            "total_active_reviewed": len(all_apps),
            "stale_threshold_days": stale_days,
        },
        warnings,
    )


async def stale_applications(
    client: GreenhouseClient,
    *,
    days: Annotated[int, Field(description="Minimum days without activity")] = 14,
    job_id: Annotated[
        int | None, Field(description="Filter to one job — list_jobs → match by name")
    ] = None,
    limit: Annotated[int, Field(description="Max applications to return")] = 50,
) -> dict[str, Any]:
    """Applications with no activity for N days, sorted by stalest. Read-only.

    Users say "who's been sitting untouched?" Use the results with bulk_reject
    for pipeline cleanup. Pass job_id (list_jobs → match by name) to filter
    to one job. Each row includes the current stage and job name.
    """
    now = datetime.now(timezone.utc)
    params: dict[str, Any] = {
        "status": "active",
        "last_activity_at[lte]": _iso(now - timedelta(days=days)),
    }
    if job_id:
        params["job_ids"] = [job_id]
    apps, warnings = await _fetch_applications(client, params)

    stale_raw: list[tuple[dict[str, Any], int]] = []
    for app in apps:
        days_inactive = _days_since(app.get("last_activity_at"), now)
        if days_inactive is not None and days_inactive >= days:
            stale_raw.append((app, days_inactive))
    stale_raw.sort(key=lambda x: x[1], reverse=True)

    stale = await _stale_rows(client, stale_raw[:limit])
    return _with_warnings(
        {
            "stale_applications": stale,
            "total_stale": len(stale_raw),
            "threshold_days": days,
            "showing": len(stale),
        },
        warnings,
    )
