"""Harvest API — Job Stages tools (3 tools)."""
from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_job_stages(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    paginate: str = "single",
) -> dict[str, Any]:
    """List all job stages across all jobs."""
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get("/job_stages", params=params, paginate=paginate)


async def list_job_stages_for_job(
    client: GreenhouseClient,
    *,
    job_id: int,
) -> dict[str, Any]:
    """List all interview stages for a specific job.

    For a full pipeline view with candidates grouped by stage, use pipeline_summary instead.
    """
    return await client.harvest_get(f"/jobs/{job_id}/stages")


async def get_job_stage(
    client: GreenhouseClient,
    *,
    job_stage_id: int,
) -> dict[str, Any]:
    """Get a single job stage by ID."""
    return await client.harvest_get_one(f"/job_stages/{job_stage_id}")
