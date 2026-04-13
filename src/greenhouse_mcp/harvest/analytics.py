"""Harvest API — Analytics and reporting tools (3 tools).

Compute recruiting KPIs from raw API data — conversion rates,
time-in-stage metrics, and source effectiveness.
"""
from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def pipeline_metrics(
    client: GreenhouseClient,
    *,
    job_id: int,
) -> dict[str, Any]:
    """Compute pipeline conversion rates and stage metrics for a job.

    Use this when a recruiter asks "what are our conversion rates?" or "where
    are we losing candidates?" Calculates: candidates per stage, stage-to-stage
    conversion rates, average time in each stage, and overall funnel metrics.

    Returns a stage-by-stage breakdown with counts, conversion percentages,
    and time metrics. One call instead of assembling data from multiple endpoints.
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)

    # Get stages
    stages_result = await client.harvest_get(
        f"/jobs/{job_id}/stages", paginate="single"
    )
    stages_list = stages_result.get("items", [])

    errors: list[dict[str, Any]] = []

    # Get ALL applications (active + rejected + hired)
    all_apps: list[dict[str, Any]] = []
    page = 1
    while True:
        result = await client.harvest_get(
            "/applications",
            params={"job_id": job_id, "per_page": 500, "page": page},
            paginate="single",
        )
        if "error" in result and "status_code" in result:
            errors.append({"step": "fetch_applications", "page": page, **result})
            break
        items = result.get("items", [])
        all_apps.extend(items)
        if not result.get("has_next"):
            break
        page += 1

    if not all_apps:
        return {
            "job_id": job_id,
            "total_applications": 0,
            "stages": [],
            "message": "No applications found for this job.",
        }

    # Count by stage and status
    stage_counts: dict[str, int] = {}
    active_by_stage: dict[str, int] = {}
    rejected_count = 0
    hired_count = 0
    total = len(all_apps)

    time_in_stage_days: dict[str, list[float]] = {}

    for app in all_apps:
        current_stage = (app.get("current_stage") or {}).get("name", "Unknown")

        if app.get("status") == "rejected":
            rejected_count += 1
        elif app.get("status") == "hired":
            hired_count += 1
        else:
            active_by_stage[current_stage] = (
                active_by_stage.get(current_stage, 0) + 1
            )

        stage_counts[current_stage] = stage_counts.get(current_stage, 0) + 1

        # Time in current stage
        last_activity = app.get("last_activity_at", "")
        applied_at = app.get("applied_at", "")
        if last_activity and applied_at:
            try:
                applied_dt = datetime.fromisoformat(
                    applied_at.replace("Z", "+00:00")
                )
                days_total = (now - applied_dt).days
                if current_stage not in time_in_stage_days:
                    time_in_stage_days[current_stage] = []
                time_in_stage_days[current_stage].append(days_total)
            except (ValueError, TypeError):
                pass

    # Build stage metrics in pipeline order
    stage_metrics = []
    for stage in stages_list:
        name = stage["name"]
        count = stage_counts.get(name, 0)
        active = active_by_stage.get(name, 0)
        conversion = round(count / total * 100, 1) if total > 0 else 0
        times = time_in_stage_days.get(name, [])
        avg_days = round(sum(times) / len(times), 1) if times else None

        stage_metrics.append({
            "stage_name": name,
            "total_reached": count,
            "currently_active": active,
            "pct_of_total": conversion,
            "avg_days_in_pipeline": avg_days,
        })

    result_data: dict[str, Any] = {
        "job_id": job_id,
        "total_applications": total,
        "active": total - rejected_count - hired_count,
        "rejected": rejected_count,
        "hired": hired_count,
        "hire_rate_pct": (
            round(hired_count / total * 100, 1) if total > 0 else 0
        ),
        "rejection_rate_pct": (
            round(rejected_count / total * 100, 1) if total > 0 else 0
        ),
        "stages": stage_metrics,
    }
    if errors:
        result_data["warnings"] = errors
        result_data["partial"] = True
    return result_data


async def source_effectiveness(
    client: GreenhouseClient,
    *,
    job_id: int | None = None,
    created_after: str | None = None,
) -> dict[str, Any]:
    """Analyze which candidate sources produce the best results.

    Use this when asked "which sources are working?" or "where should we invest
    recruiting budget?" Aggregates applications by source and calculates volume,
    active rate, and hire rate per source.

    Pass job_id to analyze a specific job, or omit for org-wide analysis.
    Use created_after (ISO date like "2025-01-01") to limit the time window.
    """
    errors: list[dict[str, Any]] = []
    params: dict[str, Any] = {"per_page": 500}
    if job_id:
        params["job_id"] = job_id
    if created_after:
        params["created_after"] = created_after

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

    # Aggregate by source
    sources: dict[str, dict[str, int]] = {}
    for app in all_apps:
        source_name = (app.get("source") or {}).get("public_name", "Unknown")
        if source_name not in sources:
            sources[source_name] = {
                "total": 0, "active": 0, "rejected": 0, "hired": 0,
            }
        sources[source_name]["total"] += 1
        status = app.get("status", "")
        if status == "rejected":
            sources[source_name]["rejected"] += 1
        elif status == "hired":
            sources[source_name]["hired"] += 1
        else:
            sources[source_name]["active"] += 1

    # Sort by total volume
    source_list = []
    for name, counts in sorted(
        sources.items(), key=lambda x: x[1]["total"], reverse=True
    ):
        total = counts["total"]
        source_list.append({
            "source": name,
            "total": total,
            "active": counts["active"],
            "rejected": counts["rejected"],
            "hired": counts["hired"],
            "hire_rate_pct": (
                round(counts["hired"] / total * 100, 1) if total > 0 else 0
            ),
        })

    result_data: dict[str, Any] = {
        "total_applications": len(all_apps),
        "unique_sources": len(source_list),
        "sources": source_list,
    }
    if errors:
        result_data["warnings"] = errors
        result_data["partial"] = True
    return result_data


async def time_to_hire(
    client: GreenhouseClient,
    *,
    job_id: int | None = None,
    created_after: str | None = None,
) -> dict[str, Any]:
    """Calculate time-to-hire metrics for hired candidates.

    Use this when asked "how long does it take to hire?" or "what's our average
    days-to-offer?" Analyzes hired applications to compute average, median, min,
    and max days from application to hire.

    Pass job_id for a specific role or omit for org-wide metrics.
    """
    from datetime import datetime

    errors: list[dict[str, Any]] = []
    params: dict[str, Any] = {"status": "hired", "per_page": 500}
    if job_id:
        params["job_id"] = job_id
    if created_after:
        params["created_after"] = created_after

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

    if not all_apps:
        return {
            "total_hires": 0,
            "message": "No hired applications found.",
        }

    days_list: list[int] = []
    hire_details: list[dict[str, Any]] = []

    for app in all_apps:
        applied_at = app.get("applied_at", "")
        # Use last_activity as proxy for hire date
        hired_at = app.get("last_activity_at", "")
        if not applied_at or not hired_at:
            continue
        try:
            applied_dt = datetime.fromisoformat(
                applied_at.replace("Z", "+00:00")
            )
            hired_dt = datetime.fromisoformat(
                hired_at.replace("Z", "+00:00")
            )
            days = (hired_dt - applied_dt).days
            if days >= 0:
                days_list.append(days)
                candidate = app.get("candidate", {})
                hire_details.append({
                    "application_id": app.get("id"),
                    "candidate_name": (
                        f'{candidate.get("first_name", "")} '
                        f'{candidate.get("last_name", "")}'
                    ).strip() if candidate else "",
                    "job_name": (
                        app.get("jobs", [{}])[0].get("name")
                        if app.get("jobs")
                        else None
                    ),
                    "applied_at": applied_at,
                    "hired_at": hired_at,
                    "days_to_hire": days,
                })
        except (ValueError, TypeError):
            continue

    if not days_list:
        return {"total_hires": len(all_apps), "message": "Could not compute dates."}

    days_list.sort()
    median_idx = len(days_list) // 2
    median = (
        days_list[median_idx]
        if len(days_list) % 2
        else (days_list[median_idx - 1] + days_list[median_idx]) // 2
    )

    result_data: dict[str, Any] = {
        "total_hires": len(days_list),
        "avg_days_to_hire": round(sum(days_list) / len(days_list), 1),
        "median_days_to_hire": median,
        "min_days": days_list[0],
        "max_days": days_list[-1],
        "recent_hires": hire_details[:20],
    }
    if errors:
        result_data["warnings"] = errors
        result_data["partial"] = True
    return result_data
