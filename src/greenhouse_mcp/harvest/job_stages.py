"""Harvest API — Job Stages tools (3 tools)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_job_stages(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    page: Annotated[int, Field(description="Page number (starts at 1)")] = 1,
    paginate: Annotated[str, Field(description="'single' for one page, 'all' to auto-fetch every page")] = "single",
) -> dict[str, Any]:
    """List all job stages across all jobs. Read-only.

    For stages on a specific job in pipeline order, use list_job_stages_for_job
    instead — it's more useful for resolving stage names to IDs.
    """
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get("/job_stages", params=params, paginate=paginate)


async def list_job_stages_for_job(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
) -> dict[str, Any]:
    """List pipeline stages for a specific job in order. Read-only.

    This is the primary tool for resolving stage names to stage IDs. When a
    user says "move to the onsite stage," use this to find the stage_id. To
    find the job_id first: list_jobs → match by name.
    """
    return await client.harvest_get(f"/jobs/{job_id}/stages")


async def get_job_stage(
    client: GreenhouseClient,
    *,
    job_stage_id: Annotated[int, Field(description="Job stage ID — get from list_job_stages_for_job")],
) -> dict[str, Any]:
    """Get a single stage by ID. Read-only.

    Returns stage name, configured interviews, and associated job.
    Usually list_job_stages_for_job is more useful — it gives all stages
    in pipeline order.
    """
    return await client.harvest_get_one(f"/job_stages/{job_stage_id}")
