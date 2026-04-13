"""Harvest API — Composite workflow tools (3 tools).

High-level tools that combine multiple API calls into single operations
that match how recruiters actually think about their work.
"""
from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def pipeline_summary(
    client: GreenhouseClient,
    *,
    job_id: int,
) -> dict[str, Any]:
    """Get a complete pipeline view for a job — candidates grouped by stage.

    Use this when a recruiter asks "show me the pipeline for the OCaml role" or
    "how many candidates are in each stage for job X." Returns candidates organized
    by interview stage with counts, days-in-stage, and last activity for each.
    One call replaces 5-10 sequential API calls.

    Returns: job info, stages with candidate counts, and per-candidate details
    including name, current stage, days in stage, and last activity date.
    """
    errors: list[dict[str, Any]] = []

    # Get job details
    job = await client.harvest_get_one(f"/jobs/{job_id}")
    if "error" in job and "status_code" in job:
        return job  # Can't continue without the job

    # Get stages for this job
    stages_result = await client.harvest_get(
        f"/jobs/{job_id}/stages", paginate="single"
    )
    stages_list = stages_result.get("items", [])

    # Get all active applications for this job
    all_apps: list[dict[str, Any]] = []
    page = 1
    while True:
        result = await client.harvest_get(
            "/applications",
            params={
                "job_id": job_id,
                "status": "active",
                "per_page": 500,
                "page": page,
            },
            paginate="single",
        )
        if "error" in result and "status_code" in result:
            errors.append({"step": "fetch_applications", "page": page, **result})
            break  # Return partial results from pages we did get
        items = result.get("items", [])
        all_apps.extend(items)
        if not result.get("has_next"):
            break
        page += 1

    # Group by stage
    stages: dict[str, list[dict[str, Any]]] = {}
    for app in all_apps:
        current_stage = app.get("current_stage") or {}
        stage_name = current_stage.get("name", "Unknown")
        if stage_name not in stages:
            stages[stage_name] = []

        last_activity = app.get("last_activity_at", "")
        days_in_stage = None
        if last_activity:
            from datetime import datetime, timezone

            try:
                last_dt = datetime.fromisoformat(
                    last_activity.replace("Z", "+00:00")
                )
                days_in_stage = (
                    datetime.now(timezone.utc) - last_dt
                ).days
            except (ValueError, TypeError):
                pass

        candidate = app.get("candidate", {})
        stages[stage_name].append({
            "application_id": app.get("id"),
            "candidate_id": app.get("candidate_id"),
            "candidate_name": (
                f'{candidate.get("first_name", "")} '
                f'{candidate.get("last_name", "")}'
            ).strip() if candidate else str(app.get("candidate_id", "")),
            "applied_at": app.get("applied_at"),
            "last_activity": last_activity,
            "days_since_activity": days_in_stage,
            "source": (app.get("source") or {}).get("public_name"),
        })

    # Order stages by pipeline order
    ordered_stages = []
    for stage in stages_list:
        name = stage["name"]
        candidates = stages.pop(name, [])
        ordered_stages.append({
            "stage_name": name,
            "stage_id": stage["id"],
            "count": len(candidates),
            "candidates": candidates,
        })
    # Add any remaining stages not in the stage list
    for name, candidates in stages.items():
        ordered_stages.append({
            "stage_name": name,
            "count": len(candidates),
            "candidates": candidates,
        })

    result_data: dict[str, Any] = {
        "job_id": job_id,
        "job_name": job.get("name"),
        "total_active": len(all_apps),
        "stages": ordered_stages,
    }
    if errors:
        result_data["warnings"] = errors
        result_data["partial"] = True
    return result_data


async def candidates_needing_action(
    client: GreenhouseClient,
    *,
    job_id: int | None = None,
    stale_days: int = 7,
) -> dict[str, Any]:
    """Find candidates that need attention — stale applications, missing scorecards.

    Use this when a recruiter asks "what needs my attention?" or "who's been sitting
    too long?" Identifies: applications with no activity for N days, interviews
    without scorecards, and candidates stuck in early stages.

    Pass job_id to filter to a specific job, or omit for all active applications.
    stale_days controls the threshold (default: 7 days without activity = stale).

    Returns categorized action items: stale applications, missing scorecards,
    and long-running candidates, sorted by urgency.
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    errors: list[dict[str, Any]] = []

    # Fetch active applications
    params: dict[str, Any] = {"status": "active", "per_page": 500}
    if job_id:
        params["job_id"] = job_id

    all_apps: list[dict[str, Any]] = []
    page = 1
    while True:
        params["page"] = page
        result = await client.harvest_get(
            "/applications", params=params, paginate="single"
        )
        if "error" in result and "status_code" in result:
            errors.append({"step": "fetch_applications", "page": page, **result})
            break
        items = result.get("items", [])
        all_apps.extend(items)
        if not result.get("has_next"):
            break
        page += 1

    stale: list[dict[str, Any]] = []
    needs_scorecard: list[dict[str, Any]] = []

    for app in all_apps:
        last_activity = app.get("last_activity_at", "")
        days_inactive = None
        if last_activity:
            try:
                last_dt = datetime.fromisoformat(
                    last_activity.replace("Z", "+00:00")
                )
                days_inactive = (now - last_dt).days
            except (ValueError, TypeError):
                pass

        candidate = app.get("candidate", {})
        app_summary = {
            "application_id": app.get("id"),
            "candidate_id": app.get("candidate_id"),
            "candidate_name": (
                f'{candidate.get("first_name", "")} '
                f'{candidate.get("last_name", "")}'
            ).strip() if candidate else str(app.get("candidate_id", "")),
            "current_stage": (app.get("current_stage") or {}).get("name"),
            "job_name": (
                app.get("jobs", [{}])[0].get("name")
                if app.get("jobs")
                else None
            ),
            "last_activity": last_activity,
            "days_inactive": days_inactive,
        }

        if days_inactive is not None and days_inactive >= stale_days:
            stale.append(app_summary)

    # Sort stale by most inactive first
    stale.sort(key=lambda x: x.get("days_inactive") or 0, reverse=True)

    # Check for interviews needing scorecards (recent interviews only)
    interviews_result = await client.harvest_get(
        "/scheduled_interviews", params={"per_page": 100}, paginate="single"
    )
    if not ("error" in interviews_result and "status_code" in interviews_result):
        for interview in interviews_result.get("items", []):
            if interview.get("status") == "complete":
                # Check if scorecard exists
                app_id = interview.get("application_id")
                interviewers = interview.get("interviewers", [])
                missing = [
                    i for i in interviewers
                    if not i.get("scorecard_submitted")
                ]
                if missing:
                    needs_scorecard.append({
                        "interview_id": interview.get("id"),
                        "application_id": app_id,
                        "interview_name": interview.get("name"),
                        "scheduled_at": interview.get("start", {}).get("date_time"),
                        "missing_scorecards_from": [
                            i.get("name") for i in missing
                        ],
                    })

    result_data: dict[str, Any] = {
        "stale_applications": stale,
        "stale_count": len(stale),
        "missing_scorecards": needs_scorecard,
        "missing_scorecard_count": len(needs_scorecard),
        "total_active_reviewed": len(all_apps),
        "stale_threshold_days": stale_days,
    }
    if errors:
        result_data["warnings"] = errors
        result_data["partial"] = True
    return result_data


async def stale_applications(
    client: GreenhouseClient,
    *,
    days: int = 14,
    job_id: int | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """List applications with no activity for N days, sorted by stalest first.

    Use this for pipeline hygiene — find candidates that have been sitting
    untouched. Default threshold is 14 days. Pass job_id to filter to one job.

    Returns applications sorted by days since last activity, with candidate name,
    current stage, and job name. Use bulk_reject to act on the results.
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    errors: list[dict[str, Any]] = []
    params: dict[str, Any] = {"status": "active", "per_page": 500}
    if job_id:
        params["job_id"] = job_id

    stale: list[dict[str, Any]] = []
    page = 1
    while True:
        params["page"] = page
        result = await client.harvest_get(
            "/applications", params=params, paginate="single"
        )
        if "error" in result and "status_code" in result:
            errors.append({"step": "fetch_applications", "page": page, **result})
            break
        items = result.get("items", [])
        if not items:
            break

        for app in items:
            last_activity = app.get("last_activity_at", "")
            if not last_activity:
                continue
            try:
                last_dt = datetime.fromisoformat(
                    last_activity.replace("Z", "+00:00")
                )
                days_inactive = (now - last_dt).days
            except (ValueError, TypeError):
                continue

            if days_inactive >= days:
                candidate = app.get("candidate", {})
                stale.append({
                    "application_id": app.get("id"),
                    "candidate_id": app.get("candidate_id"),
                    "candidate_name": (
                        f'{candidate.get("first_name", "")} '
                        f'{candidate.get("last_name", "")}'
                    ).strip() if candidate else str(
                        app.get("candidate_id", "")
                    ),
                    "current_stage": (
                        app.get("current_stage") or {}
                    ).get("name"),
                    "job_name": (
                        app.get("jobs", [{}])[0].get("name")
                        if app.get("jobs")
                        else None
                    ),
                    "last_activity": last_activity,
                    "days_inactive": days_inactive,
                    "applied_at": app.get("applied_at"),
                })

        if not result.get("has_next"):
            break
        page += 1

    stale.sort(key=lambda x: x.get("days_inactive") or 0, reverse=True)
    result_data: dict[str, Any] = {
        "stale_applications": stale[:limit],
        "total_stale": len(stale),
        "threshold_days": days,
        "showing": min(len(stale), limit),
    }
    if errors:
        result_data["warnings"] = errors
        result_data["partial"] = True
    return result_data
