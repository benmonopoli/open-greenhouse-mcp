"""Harvest API — Jobs tools (4 tools).

Also holds small private helpers shared by the other Group B modules (job posts,
stages, openings, offers, interviews, scorecards) for resolving v3 id references
into names with batched lookups.
"""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient, add_date_filter
from greenhouse_mcp.harvest._custom_field_merge import merged_custom_fields

# ---------------------------------------------------------------------------
# Private helpers (not registered as tools — names start with "_")
# ---------------------------------------------------------------------------


async def _lookup(
    client: GreenhouseClient,
    endpoint: str,
    ids: Any,
    warnings: list[str],
    *,
    filter_name: str = "ids",
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Batched fetch of ``endpoint`` filtered by ``filter_name`` (50 ids per call).

    On failure, records a warning and returns [] so callers can degrade gracefully.
    """
    wanted = {i for i in ids if isinstance(i, int)}
    if not wanted:
        return []
    result = await client.harvest_get_ids(endpoint, filter_name, wanted, params=params)
    if client._is_error(result):
        warnings.append(
            f"Could not load {endpoint} ({result.get('status_code')}): {result.get('error')}"
        )
        return []
    return list(result.get("items", []))


def _by_id(items: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {i["id"]: i for i in items if isinstance(i, dict) and "id" in i}


def _user_name(user: dict[str, Any] | None) -> str | None:
    if not user:
        return None
    name = user.get("name") or " ".join(
        p for p in (user.get("first_name"), user.get("last_name")) if p
    )
    return name or user.get("primary_email")


def _user_ref(user_id: int | None, users: dict[int, dict[str, Any]]) -> dict[str, Any] | None:
    if user_id is None:
        return None
    user = users.get(user_id)
    return {
        "id": user_id,
        "name": _user_name(user),
        "email": user.get("primary_email") if user else None,
    }


def _with_warnings(result: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    if warnings:
        result["warnings"] = warnings
    return result


def _v3_custom_fields(custom_fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Accept v1-style ``{id, value}`` entries and convert to v3 ``{custom_field_id, value}``.

    Entries already using ``custom_field_id`` or ``name_key`` pass through unchanged.
    """
    out: list[dict[str, Any]] = []
    for cf in custom_fields:
        entry = dict(cf)
        if "custom_field_id" not in entry and "name_key" not in entry and "id" in entry:
            entry["custom_field_id"] = entry.pop("id")
        out.append(entry)
    return out


async def _hydrate_jobs(
    client: GreenhouseClient, jobs: list[dict[str, Any]], warnings: list[str]
) -> None:
    """Add ``department`` and ``offices`` ({id, name}) to each job, in place."""
    dept_ids = {j.get("department_id") for j in jobs}
    office_ids = {o for j in jobs for o in (j.get("office_ids") or [])}
    depts, offices = await asyncio.gather(
        _lookup(client, "/departments", dept_ids, warnings),
        _lookup(client, "/offices", office_ids, warnings),
    )
    dept_map, office_map = _by_id(depts), _by_id(offices)
    for job in jobs:
        dept_id = job.get("department_id")
        job["department"] = (
            {"id": dept_id, "name": dept_map.get(dept_id, {}).get("name")}
            if dept_id is not None
            else None
        )
        job["offices"] = [
            {"id": o, "name": office_map.get(o, {}).get("name")}
            for o in (job.get("office_ids") or [])
        ]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


async def list_jobs(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    cursor: Annotated[
        str | None,
        Field(description="Pass next_cursor from the previous response to get the next page"),
    ] = None,
    status: Annotated[
        str | None, Field(description="Filter by status: 'open', 'closed', or 'draft'")
    ] = None,
    department_id: Annotated[
        int | None, Field(description="Filter to jobs in this department")
    ] = None,
    office_id: Annotated[int | None, Field(description="Filter to jobs in this office")] = None,
    created_after: Annotated[
        str | None, Field(description="ISO 8601 datetime — only jobs created at/after this")
    ] = None,
    created_before: Annotated[
        str | None, Field(description="ISO 8601 datetime — only jobs created before this")
    ] = None,
    requisition_id: Annotated[
        str | None, Field(description="Only jobs with this exact external requisition ID")
    ] = None,
    paginate: Annotated[
        str, Field(description="'single' for one page, 'all' to auto-fetch every page")
    ] = "single",
) -> dict[str, Any]:
    """List all jobs with optional filters. Read-only.

    This is the primary tool for resolving job titles to job IDs. When a user
    mentions a job by name ("Backend Engineer"), use this to find the matching
    job_id. Filter by status ('open'/'closed'/'draft'), department_id
    (list_departments), or office_id (list_offices). Each job includes
    department and offices as {id, name}. Openings are not embedded — use
    list_job_openings; the hiring team is on get_job. For pipeline views, use
    pipeline_summary with the job_id.
    """
    params: dict[str, Any] = {
        "per_page": per_page,
        "cursor": cursor,
        "status": status,
        "department_id": department_id,
        "office_id": office_id,
        "requisition_id": requisition_id,
    }
    add_date_filter(params, "created_at", gte=created_after, lt=created_before)
    result = await client.harvest_get("/jobs", params=params, paginate=paginate)
    if client._is_error(result):
        return result
    warnings: list[str] = []
    await _hydrate_jobs(client, result.get("items", []), warnings)
    return _with_warnings(result, warnings)


async def get_job(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
) -> dict[str, Any]:
    """Get full details for a job by ID. Read-only.

    Returns name, status, requisition_id, notes, custom fields, department and
    offices ({id, name}), openings, and the hiring team (hiring_managers,
    recruiters, coordinators, sourcers as {id, name, email}). Use list_jobs to
    find the job_id by name first. For the public listing, use
    list_job_posts_for_job. For pipeline stages, use list_job_stages_for_job.
    """
    job = await client.harvest_get_by_id("/jobs", job_id)
    if client._is_error(job):
        return job
    warnings: list[str] = []
    jid = [job_id]
    _, openings, managers, owners = await asyncio.gather(
        _hydrate_jobs(client, [job], warnings),
        _lookup(client, "/openings", jid, warnings, filter_name="job_ids"),
        _lookup(client, "/job_hiring_managers", jid, warnings, filter_name="job_ids"),
        _lookup(client, "/job_owners", jid, warnings, filter_name="job_ids"),
    )
    user_ids = {m.get("user_id") for m in managers} | {o.get("user_id") for o in owners}
    users = _by_id(await _lookup(client, "/users", user_ids, warnings))

    team: dict[str, list[dict[str, Any]]] = {
        "hiring_managers": [],
        "recruiters": [],
        "coordinators": [],
        "sourcers": [],
    }
    for m in managers:
        ref = _user_ref(m.get("user_id"), users)
        if ref:
            team["hiring_managers"].append(ref)
    for o in owners:
        ref = _user_ref(o.get("user_id"), users)
        key = f"{o.get('type')}s"
        if ref and key in team:
            ref["responsible"] = bool(o.get("responsible"))
            team[key].append(ref)
    job["openings"] = sorted(openings, key=lambda o: o.get("sort_order") or 0)
    job["hiring_team"] = team
    return _with_warnings(job, warnings)


async def create_job(
    client: GreenhouseClient,
    *,
    template_job_id: Annotated[
        int,
        Field(
            description="Existing job ID to use as template — copies pipeline stages and settings"
        ),
    ],
    number_of_openings: Annotated[
        int, Field(description="Number of openings to create on this job")
    ] = 1,
    job_post_name: Annotated[str | None, Field(description="Title for the public job post")] = None,
    job_name: Annotated[str | None, Field(description="Internal job name")] = None,
    department_id: Annotated[
        int | None, Field(description="Department ID — get from list_departments")
    ] = None,
    office_ids: Annotated[
        list[int] | None, Field(description="Office IDs — get from list_offices")
    ] = None,
    requisition_id: Annotated[
        str | None, Field(description="External requisition/req ID for HRIS mapping")
    ] = None,
    notes: Annotated[
        str | None, Field(description="Internal notes about the job (HTML supported)")
    ] = None,
    opening_ids: Annotated[
        list[str] | None,
        Field(description="Optional external IDs for the new openings, one per opening"),
    ] = None,
    custom_fields: Annotated[
        list[dict[str, Any]] | None,
        Field(description="Array of {id, value} — get field IDs from list_custom_fields"),
    ] = None,
) -> dict[str, Any]:
    """Create a new job from a template. Write operation — admin only.

    Users say "create a new Backend Engineer role." Requires template_job_id —
    use list_jobs to find a similar existing job. For department_id:
    list_departments → match by name. For office_ids: list_offices → match.
    After creation, use update_job_post to set the public listing content.
    """
    json_data: dict[str, Any] = {
        "template_job_id": template_job_id,
        "number_of_openings": number_of_openings,
    }
    optional = {
        "job_post_name": job_post_name,
        "job_name": job_name,
        "department_id": department_id,
        "office_ids": office_ids,
        "requisition_id": requisition_id,
        "notes": notes,
        "opening_ids": opening_ids,
    }
    json_data.update({k: v for k, v in optional.items() if v is not None})
    if custom_fields is not None:
        json_data["custom_fields"] = _v3_custom_fields(custom_fields)
    return await client.harvest_post("/jobs", json_data=json_data)


async def update_job(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    name: Annotated[str | None, Field(description="New internal job name")] = None,
    status: Annotated[
        str | None,
        Field(
            description="Not settable in Harvest v3 — a job's status follows its openings. "
            "Use update_job_opening to close or reopen openings instead."
        ),
    ] = None,
    department_id: Annotated[
        int | None, Field(description="New department ID — get from list_departments")
    ] = None,
    office_ids: Annotated[
        list[int] | None,
        Field(description="Replaces all office associations — get IDs from list_offices"),
    ] = None,
    requisition_id: Annotated[str | None, Field(description="External requisition/req ID")] = None,
    notes: Annotated[
        str | None, Field(description="Internal notes about the job (HTML supported)")
    ] = None,
    team_and_responsibilities: Annotated[
        str | None, Field(description="Internal description of the team and responsibilities")
    ] = None,
    how_to_sell_this_job: Annotated[
        str | None, Field(description="Internal selling points recruiters use for the role")
    ] = None,
    custom_fields: Annotated[
        list[dict[str, Any]] | None,
        Field(description="Array of {id, value} — replaces the job's custom field values"),
    ] = None,
) -> dict[str, Any]:
    """Update a job's name, department, offices, notes, or custom fields. Write operation.

    To find job_id: list_jobs → match by name. Only updates fields you provide.
    For department_id: list_departments. For office_ids: list_offices. To modify
    the public listing, use update_job_post instead. A job's open/closed status
    can't be set directly in Harvest v3: close its openings with
    update_job_opening(status='closed') (list_job_openings to find them).
    """
    if status is not None:
        return {
            "error": "Harvest v3 doesn't allow setting a job's status directly. A job is "
            "open while it has open openings: use list_job_openings and "
            "update_job_opening(status='closed' or 'open') instead.",
            "status_code": 422,
        }
    json_data: dict[str, Any] = {}
    optional = {
        "name": name,
        "department_id": department_id,
        "office_ids": office_ids,
        "requisition_id": requisition_id,
        "notes": notes,
        "team_and_responsibilities": team_and_responsibilities,
        "how_to_sell_this_job": how_to_sell_this_job,
    }
    json_data.update({k: v for k, v in optional.items() if v is not None})
    if custom_fields is not None:
        # v3 replaces the whole collection: send current values plus this change.
        merged = await merged_custom_fields(client, "/jobs", job_id, custom_fields)
        if client._is_error(merged):
            return merged  # type: ignore[return-value]
        json_data["custom_fields"] = merged
    return await client.harvest_patch(f"/jobs/{job_id}", json_data=json_data)
