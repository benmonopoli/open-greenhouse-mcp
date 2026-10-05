"""Harvest API — Job Stages tools (3 tools).

v3 calls pipeline stages ``job_interview_stages`` (ordered by ``sort_order``) and the
interviews configured on each stage ``job_interviews``.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient
from greenhouse_mcp.harvest.jobs import _lookup, _with_warnings


def _sort_key(item: dict[str, Any]) -> tuple[int, int]:
    return (item.get("sort_order") or 0, item.get("id") or 0)


def _attach_interviews(
    stages: list[dict[str, Any]], interviews: list[dict[str, Any]]
) -> None:
    by_stage: dict[int, list[dict[str, Any]]] = {}
    for iv in sorted(interviews, key=_sort_key):
        by_stage.setdefault(iv.get("job_interview_stage_id") or 0, []).append(iv)
    for stage in stages:
        stage["interviews"] = by_stage.get(stage.get("id") or 0, [])


async def list_job_stages(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    cursor: Annotated[
        str | None,
        Field(description="Pass next_cursor from the previous response to get the next page"),
    ] = None,
    active: Annotated[
        bool | None,
        Field(description="true for stages on current interview plans only, false for removed"),
    ] = None,
    paginate: Annotated[
        str, Field(description="'single' for one page, 'all' to auto-fetch every page")
    ] = "single",
) -> dict[str, Any]:
    """List all job stages across all jobs. Read-only.

    Returns stage id, job_id, name, sort_order, and active. For stages on a
    specific job in pipeline order (with their interviews), use
    list_job_stages_for_job instead — it's more useful for resolving stage
    names to IDs.
    """
    params: dict[str, Any] = {"per_page": per_page, "cursor": cursor, "active": active}
    return await client.harvest_get("/job_interview_stages", params=params, paginate=paginate)


async def list_job_stages_for_job(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    include_inactive: Annotated[
        bool, Field(description="Also return stages removed from the job's interview plan")
    ] = False,
) -> dict[str, Any]:
    """List pipeline stages for a specific job in order. Read-only.

    This is the primary tool for resolving stage names to stage IDs. When a
    user says "move to the onsite stage," use this to find the stage_id (the
    job_interview_stage_id used by move/advance). Stages are sorted by
    sort_order, and each has an interviews array (the stage's configured
    interviews — their id is the interview_id that create_interview expects;
    scheduling_type 'needs_scheduling' means it is a calendared interview).
    To find the job_id first: list_jobs → match by name.
    """
    params: dict[str, Any] = {"job_ids": [job_id], "per_page": 500}
    if not include_inactive:
        params["active"] = True
    stages = await client.harvest_get("/job_interview_stages", params=params, paginate="all")
    if client._is_error(stages):
        return stages
    items = sorted(stages.get("items", []), key=_sort_key)
    warnings: list[str] = []
    iv_params = {"active": True} if not include_inactive else None
    interviews = await _lookup(
        client, "/job_interviews", [job_id] if items else [], warnings,
        filter_name="job_ids", params=iv_params,
    )
    _attach_interviews(items, interviews)
    return _with_warnings({"items": items, "total": len(items)}, warnings)


async def get_job_stage(
    client: GreenhouseClient,
    *,
    job_stage_id: Annotated[
        int, Field(description="Job stage ID — get from list_job_stages_for_job")
    ],
) -> dict[str, Any]:
    """Get a single stage by ID. Read-only.

    Returns stage name, sort_order, job_id, and its configured interviews.
    Usually list_job_stages_for_job is more useful — it gives all stages
    in pipeline order.
    """
    stage = await client.harvest_get_by_id("/job_interview_stages", job_stage_id)
    if client._is_error(stage):
        return stage
    warnings: list[str] = []
    interviews = await _lookup(
        client, "/job_interviews", [job_stage_id], warnings,
        filter_name="job_interview_stage_ids",
    )
    _attach_interviews([stage], interviews)
    return _with_warnings(stage, warnings)
