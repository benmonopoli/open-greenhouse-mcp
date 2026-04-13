"""Harvest API — Jobs tools (4 tools)."""
from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_jobs(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    status: str | None = None,
    department_id: int | None = None,
    office_id: int | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
    paginate: str = "single",
) -> dict[str, Any]:
    """List all jobs with optional filters for status, department, office, dates."""
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    if status is not None:
        params["status"] = status
    if department_id is not None:
        params["department_id"] = department_id
    if office_id is not None:
        params["office_id"] = office_id
    if created_after is not None:
        params["created_after"] = created_after
    if created_before is not None:
        params["created_before"] = created_before
    return await client.harvest_get("/jobs", params=params, paginate=paginate)


async def get_job(
    client: GreenhouseClient,
    *,
    job_id: int,
) -> dict[str, Any]:
    """Get a single job by ID."""
    return await client.harvest_get(f"/jobs/{job_id}")


async def create_job(
    client: GreenhouseClient,
    *,
    template_job_id: int,
    number_of_openings: int = 1,
    job_post_name: str | None = None,
    job_name: str | None = None,
    department_id: int | None = None,
    office_ids: list[int] | None = None,
    requisition_id: str | None = None,
) -> dict[str, Any]:
    """Create a new job from a template with optional name, department, and offices."""
    json_data: dict[str, Any] = {
        "template_job_id": template_job_id,
        "number_of_openings": number_of_openings,
    }
    if job_post_name is not None:
        json_data["job_post_name"] = job_post_name
    if job_name is not None:
        json_data["job_name"] = job_name
    if department_id is not None:
        json_data["department_id"] = department_id
    if office_ids is not None:
        json_data["office_ids"] = office_ids
    if requisition_id is not None:
        json_data["requisition_id"] = requisition_id
    return await client.harvest_post("/jobs", json_data=json_data)


async def update_job(
    client: GreenhouseClient,
    *,
    job_id: int,
    name: str | None = None,
    status: str | None = None,
    department_id: int | None = None,
    office_ids: list[int] | None = None,
    requisition_id: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Update a job's name, status, department, offices, requisition ID, or notes."""
    json_data: dict[str, Any] = {}
    if name is not None:
        json_data["name"] = name
    if status is not None:
        json_data["status"] = status
    if department_id is not None:
        json_data["department_id"] = department_id
    if office_ids is not None:
        json_data["office_ids"] = office_ids
    if requisition_id is not None:
        json_data["requisition_id"] = requisition_id
    if notes is not None:
        json_data["notes"] = notes
    return await client.harvest_patch(f"/jobs/{job_id}", json_data=json_data)
