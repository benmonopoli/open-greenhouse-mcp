"""Harvest API — Jobs tools (4 tools)."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_jobs(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    page: Annotated[int, Field(description="Page number (starts at 1)")] = 1,
    status: Annotated[
        str | None, Field(description="Filter by status: 'open', 'closed', or 'draft'")
    ] = None,
    department_id: Annotated[
        int | None, Field(description="Filter to jobs in this department")
    ] = None,
    office_id: Annotated[int | None, Field(description="Filter to jobs in this office")] = None,
    created_after: Annotated[
        str | None, Field(description="ISO 8601 datetime — only jobs created after this")
    ] = None,
    created_before: Annotated[
        str | None, Field(description="ISO 8601 datetime — only jobs created before this")
    ] = None,
    paginate: Annotated[
        str, Field(description="'single' for one page, 'all' to auto-fetch every page")
    ] = "single",
) -> dict[str, Any]:
    """List all jobs with optional filters. Read-only.

    This is the primary tool for resolving job titles to job IDs. When a user
    mentions a job by name ("Backend Engineer"), use this to find the matching
    job_id. Filter by status ('open'/'closed'/'draft'), department_id
    (list_departments), or office_id (list_offices). For pipeline views, use
    pipeline_summary with the job_id.
    """
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
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
) -> dict[str, Any]:
    """Get full details for a job by ID. Read-only.

    Returns name, status, departments, offices, hiring team, and custom fields.
    Use list_jobs to find the job_id by name first. For the public listing, use
    list_job_posts_for_job. For pipeline stages, use list_job_stages_for_job.
    """
    return await client.harvest_get_one(f"/jobs/{job_id}")


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
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    name: Annotated[str | None, Field(description="New internal job name")] = None,
    status: Annotated[
        str | None, Field(description="New status: 'open', 'closed', or 'draft'")
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
) -> dict[str, Any]:
    """Update a job's name, status, department, offices, or notes. Write operation.

    To find job_id: list_jobs → match by name. Only updates fields you provide.
    For department_id: list_departments. For office_ids: list_offices. To modify
    the public listing, use update_job_post instead.
    """
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
