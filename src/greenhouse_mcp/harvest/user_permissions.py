"""Harvest API — User Permissions tools (6 tools)."""
from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_job_permissions(
    client: GreenhouseClient,
    *,
    user_id: int,
) -> dict[str, Any]:
    """List all job-level permissions granted to a user."""
    return await client.harvest_get(f"/users/{user_id}/permissions/jobs")


async def add_job_permission(
    client: GreenhouseClient,
    *,
    user_id: int,
    job_id: int,
    user_role_id: int,
) -> dict[str, Any]:
    """Grant a user a specific role on a job."""
    json_data: dict[str, Any] = {"job_id": job_id, "user_role_id": user_role_id}
    return await client.harvest_post(f"/users/{user_id}/permissions/jobs", json_data=json_data)


async def remove_job_permission(
    client: GreenhouseClient,
    *,
    user_id: int,
    job_permission_id: int,
) -> dict[str, Any]:
    """Revoke a user's job permission by permission ID."""
    return await client.harvest_delete(
        f"/users/{user_id}/permissions/jobs/{job_permission_id}"
    )


async def list_future_job_permissions(
    client: GreenhouseClient,
    *,
    user_id: int,
) -> dict[str, Any]:
    """List a user's future job permissions (auto-applied to new jobs by office/department)."""
    return await client.harvest_get(f"/users/{user_id}/permissions/future_jobs")


async def add_future_job_permission(
    client: GreenhouseClient,
    *,
    user_id: int,
    user_role_id: int,
    office_id: int | None = None,
    department_id: int | None = None,
) -> dict[str, Any]:
    """Grant a user a role on all future jobs, optionally scoped to an office or department."""
    json_data: dict[str, Any] = {"user_role_id": user_role_id}
    if office_id is not None:
        json_data["office_id"] = office_id
    if department_id is not None:
        json_data["department_id"] = department_id
    return await client.harvest_post(
        f"/users/{user_id}/permissions/future_jobs", json_data=json_data
    )


async def remove_future_job_permission(
    client: GreenhouseClient,
    *,
    user_id: int,
    future_job_permission_id: int,
) -> dict[str, Any]:
    """Revoke a user's future job permission by permission ID."""
    return await client.harvest_delete(
        f"/users/{user_id}/permissions/future_jobs/{future_job_permission_id}"
    )
