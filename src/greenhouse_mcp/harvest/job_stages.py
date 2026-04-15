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

    Returns stages globally. For stages on a specific job (which you almost always
    want), use list_job_stages_for_job instead. Stage IDs are needed for
    advance_application, move_application_same_job, and create_interview.
    """
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get("/job_stages", params=params, paginate=paginate)


async def list_job_stages_for_job(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
) -> dict[str, Any]:
    """List all interview stages for a specific job in pipeline order. Read-only.

    Returns the ordered list of stages a candidate moves through. Stage IDs are
    needed for advance_application (from_stage_id, to_stage_id),
    move_application_same_job, and create_interview (interview_id). For stages
    across all jobs, use list_job_stages.
    """
    return await client.harvest_get(f"/jobs/{job_id}/stages")


async def get_job_stage(
    client: GreenhouseClient,
    *,
    job_stage_id: Annotated[int, Field(description="Job stage ID — get from list_job_stages_for_job")],
) -> dict[str, Any]:
    """Get a single job stage by ID. Read-only. Returns the stage name, interviews
    configured at this stage, and associated job.

    Use list_job_stages_for_job to find stage IDs for a specific job.
    """
    return await client.harvest_get_one(f"/job_stages/{job_stage_id}")
