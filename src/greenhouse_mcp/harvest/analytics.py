"""Harvest API — Analytics and reporting tools (3 tools).

Compute recruiting KPIs from raw API data — conversion rates,
time-in-stage metrics, and source effectiveness.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient, add_date_filter
from greenhouse_mcp.harvest.workflows import (
    _days_since,
    _fetch_applications,
    _is_error,
    _job_stages,
    _parse_dt,
    _resolve_candidate_names,
    _resolve_names,
    _simple_status,
    _to_datetime,
    _with_warnings,
)


async def pipeline_metrics(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID — list_jobs → match by name")],
) -> dict[str, Any]:
    """Conversion rates and stage metrics for a job. Read-only.

    Users say "what are our conversion rates for the Backend role?" or "where
    are we losing candidates?" To find job_id: list_jobs → match by name.
    Returns, per interview stage in pipeline order: how many applications ever
    reached it, how many are there now, % of all applications, stage-to-next
    conversion, and average days spent in the stage (from stage history).
    """
    now = datetime.now(timezone.utc)

    stages_list = await _job_stages(client, [job_id])
    all_apps, warnings = await _fetch_applications(client, {"job_ids": [job_id]})

    if not all_apps:
        return _with_warnings(
            {
                "job_id": job_id,
                "total_applications": 0,
                "stages": [],
                "message": "No applications found for this job.",
            },
            warnings,
        )

    apps_by_id = {a["id"]: a for a in all_apps if a.get("id") is not None}
    total = len(all_apps)
    rejected_count = sum(1 for a in all_apps if a.get("status") == "rejected")
    hired_count = sum(1 for a in all_apps if a.get("status") == "hired")

    # Current position of active applications, and pipeline age per current stage
    active_by_stage: dict[Any, int] = {}
    pipeline_age: dict[Any, list[int]] = {}
    for app in all_apps:
        key = app.get("job_interview_stage_id")
        if _simple_status(app.get("status")) == "active":
            active_by_stage[key] = active_by_stage.get(key, 0) + 1
            age = _days_since(app.get("created_at"), now)
            if age is not None:
                pipeline_age.setdefault(key, []).append(age)

    # Stage history: every stage each application has visited on this job.
    reached: dict[int, set[int]] = {}
    days_in: dict[int, list[int]] = {}
    history_ok = False
    stage_ids = [s["id"] for s in stages_list]
    if stage_ids:
        history = await client.harvest_get_ids(
            "/application_stages",
            "job_interview_stage_ids",
            stage_ids,
            params={"per_page": 500},
        )
        if _is_error(history):
            warnings.append({"step": "fetch_application_stages", **history})
        else:
            history_ok = True
            for row in history.get("items", []):
                app_id = row.get("application_id")
                sid = row.get("job_interview_stage_id")
                # Rows exist for every stage on the plan; unvisited ones have no entered_at
                if app_id not in apps_by_id or sid is None or not row.get("entered_at"):
                    continue
                reached.setdefault(sid, set()).add(app_id)
                if row.get("days_in_stage") is not None:
                    days_in.setdefault(sid, []).append(int(row["days_in_stage"]))

    if not history_ok:
        # Fall back to current stage only
        for app in all_apps:
            sid = app.get("job_interview_stage_id")
            if sid is not None:
                reached.setdefault(sid, set()).add(app["id"])

    stage_metrics: list[dict[str, Any]] = []
    visible = [s for s in stages_list if s.get("active", True) or reached.get(s["id"])]
    for idx, stage in enumerate(visible):
        sid = stage["id"]
        count = len(reached.get(sid, set()))
        nxt = visible[idx + 1]["id"] if idx + 1 < len(visible) else None
        next_count = len(reached.get(nxt, set())) if nxt is not None else None
        times = days_in.get(sid, [])
        ages = pipeline_age.get(sid, [])
        stage_metrics.append(
            {
                "stage_name": stage.get("name"),
                "stage_id": sid,
                "total_reached": count,
                "currently_active": active_by_stage.get(sid, 0),
                "pct_of_total": round(count / total * 100, 1) if total else 0,
                "conversion_to_next_pct": (
                    round(next_count / count * 100, 1)
                    if next_count is not None and count
                    else None
                ),
                "avg_days_in_stage": round(sum(times) / len(times), 1) if times else None,
                "avg_days_in_pipeline": round(sum(ages) / len(ages), 1) if ages else None,
            }
        )

    result_data: dict[str, Any] = {
        "job_id": job_id,
        "total_applications": total,
        "active": total - rejected_count - hired_count,
        "rejected": rejected_count,
        "hired": hired_count,
        "hire_rate_pct": round(hired_count / total * 100, 1) if total else 0,
        "rejection_rate_pct": round(rejected_count / total * 100, 1) if total else 0,
        "stages": stage_metrics,
        "reached_counts_from": "stage_history" if history_ok else "current_stage_only",
    }
    return _with_warnings(result_data, warnings)


async def source_effectiveness(
    client: GreenhouseClient,
    *,
    job_id: Annotated[
        int | None, Field(description="Filter to one job — list_jobs → match by name")
    ] = None,
    created_after: Annotated[
        str | None, Field(description="ISO 8601 date — only applications created after this")
    ] = None,
) -> dict[str, Any]:
    """Which candidate sources produce the best results. Read-only.

    Users say "which sources are working?" or "where should we spend
    recruiting budget?" Pass job_id (list_jobs → match by name) for one
    role, or omit for org-wide analysis. Returns volume, active, rejected,
    hired and hire rate per source, with each source's strategy (e.g. Referral).
    """
    params: dict[str, Any] = {}
    if job_id:
        params["job_ids"] = [job_id]
    if created_after:
        add_date_filter(params, "created_at", gt=_to_datetime(created_after))
    all_apps, warnings = await _fetch_applications(client, params)

    source_ids = {a["source_id"] for a in all_apps if a.get("source_id")}
    source_info: dict[int, dict[str, Any]] = {}
    if source_ids:
        res = await client.harvest_get_ids(
            "/sources", "ids", sorted(source_ids), params={"per_page": 100}
        )
        if _is_error(res):
            warnings.append({"step": "fetch_sources", **res})
        else:
            source_info = {s["id"]: s for s in res.get("items", []) if "id" in s}

    sources: dict[Any, dict[str, Any]] = {}
    for app in all_apps:
        sid = app.get("source_id")
        if sid not in sources:
            info = source_info.get(sid) if sid else None
            sources[sid] = {
                "source": (info or {}).get("name") or ("Unknown" if not sid else str(sid)),
                "source_id": sid,
                "strategy": ((info or {}).get("type") or {}).get("name"),
                "total": 0,
                "active": 0,
                "rejected": 0,
                "hired": 0,
            }
        entry = sources[sid]
        entry["total"] += 1
        status = app.get("status", "")
        if status == "rejected":
            entry["rejected"] += 1
        elif status == "hired":
            entry["hired"] += 1
        else:
            entry["active"] += 1

    source_list = sorted(sources.values(), key=lambda s: s["total"], reverse=True)
    for entry in source_list:
        entry["hire_rate_pct"] = (
            round(entry["hired"] / entry["total"] * 100, 1) if entry["total"] else 0
        )

    return _with_warnings(
        {
            "total_applications": len(all_apps),
            "unique_sources": len(source_list),
            "sources": source_list,
        },
        warnings,
    )


async def time_to_hire(
    client: GreenhouseClient,
    *,
    job_id: Annotated[
        int | None, Field(description="Filter to one job — list_jobs → match by name")
    ] = None,
    created_after: Annotated[
        str | None, Field(description="ISO 8601 date — limit analysis window")
    ] = None,
) -> dict[str, Any]:
    """Time-to-hire metrics for hired candidates. Read-only.

    Users say "how long does it take to hire?" or "what's our average
    days-to-offer?" Pass job_id (list_jobs → match by name) for one role,
    or omit for org-wide metrics. Returns average, median, min, max days from
    application to hire. The hire date is the accepted offer's resolved date
    when available, otherwise the application's last activity.
    """
    params: dict[str, Any] = {"status": "hired"}
    if job_id:
        params["job_ids"] = [job_id]
    if created_after:
        add_date_filter(params, "created_at", gt=_to_datetime(created_after))
    all_apps, warnings = await _fetch_applications(client, params)

    if not all_apps:
        return _with_warnings(
            {"total_hires": 0, "message": "No hired applications found."}, warnings
        )

    app_ids = [a["id"] for a in all_apps if a.get("id") is not None]
    accepted_at: dict[Any, str] = {}
    offers = await client.harvest_get_ids(
        "/offers",
        "application_ids",
        app_ids,
        params={"status": "Accepted", "per_page": 500},
    )
    if _is_error(offers):
        warnings.append({"step": "fetch_offers", **offers})
    else:
        for offer in offers.get("items", []):
            aid, resolved = offer.get("application_id"), offer.get("resolved_at")
            if aid is not None and resolved and resolved > accepted_at.get(aid, ""):
                accepted_at[aid] = resolved

    names = await _resolve_candidate_names(
        client, {a["candidate_id"] for a in all_apps if a.get("candidate_id")}
    )
    jobs = await _resolve_names(client, "/jobs", {a["job_id"] for a in all_apps if a.get("job_id")})

    days_list: list[int] = []
    hire_details: list[dict[str, Any]] = []
    for app in all_apps:
        applied_at = app.get("created_at") or ""
        hired_at = accepted_at.get(app.get("id")) or app.get("last_activity_at") or ""
        applied_dt, hired_dt = _parse_dt(applied_at), _parse_dt(hired_at)
        if not applied_dt or not hired_dt:
            continue
        days = (hired_dt - applied_dt).days
        if days < 0:
            continue
        days_list.append(days)
        cid = app.get("candidate_id")
        hire_details.append(
            {
                "application_id": app.get("id"),
                "candidate_name": names.get(cid, str(cid)) if cid else "",
                "job_name": jobs.get(app["job_id"]) if app.get("job_id") else None,
                "applied_at": applied_at,
                "hired_at": hired_at,
                "hired_at_source": (
                    "accepted_offer" if app.get("id") in accepted_at else "last_activity"
                ),
                "days_to_hire": days,
            }
        )

    if not days_list:
        return _with_warnings(
            {"total_hires": len(all_apps), "message": "Could not compute dates."}, warnings
        )

    hire_details.sort(key=lambda h: h["hired_at"], reverse=True)
    days_list.sort()
    median_idx = len(days_list) // 2
    median = (
        days_list[median_idx]
        if len(days_list) % 2
        else (days_list[median_idx - 1] + days_list[median_idx]) // 2
    )

    return _with_warnings(
        {
            "total_hires": len(days_list),
            "avg_days_to_hire": round(sum(days_list) / len(days_list), 1),
            "median_days_to_hire": median,
            "min_days": days_list[0],
            "max_days": days_list[-1],
            "recent_hires": hire_details[:20],
        },
        warnings,
    )
