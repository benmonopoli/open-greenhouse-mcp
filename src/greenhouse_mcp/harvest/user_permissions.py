"""Harvest API — User Permissions tools (6 tools)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_job_permissions(
    client: GreenhouseClient,
    *,
    user_id: Annotated[int, Field(description="Greenhouse user ID — get from list_users")],
) -> dict[str, Any]:
    """List all job-level permissions for a user. Read-only.

    To find user_id: list_users → match by name or email.
    """
    return await client.harvest_get(f"/users/{user_id}/permissions/jobs")


async def add_job_permission(
    client: GreenhouseClient,
    *,
    user_id: Annotated[int, Field(description="Greenhouse user ID — get from list_users")],
    job_id: Annotated[int, Field(description="Job to grant access to — get from list_jobs")],
    user_role_id: Annotated[int, Field(description="Role on this job — get valid IDs from list_user_roles")],
) -> dict[str, Any]:
    """Grant a user a role on a specific job. Write operation — admin only.

    Users say "give Sarah recruiter access to the Backend role." For user_id:
    list_users → match by name. For job_id: list_jobs → match by name. For
    user_role_id: list_user_roles → match by role name.
    """
    json_data: dict[str, Any] = {"job_id": job_id, "user_role_id": user_role_id}
    return await client.harvest_post(f"/users/{user_id}/permissions/jobs", json_data=json_data)


async def remove_job_permission(
    client: GreenhouseClient,
    *,
    user_id: Annotated[int, Field(description="Greenhouse user ID — get from list_users")],
    job_permission_id: Annotated[int, Field(description="Permission ID to revoke — get from list_job_permissions")],
) -> dict[str, Any]:
    """Revoke a user's job-level permission. Write operation — admin only.

    To find user_id: list_users → match by name. For the permission ID:
    list_job_permissions for the user → match the job.
    """
    return await client.harvest_delete(
        f"/users/{user_id}/permissions/jobs/{job_permission_id}"
    )


async def list_future_job_permissions(
    client: GreenhouseClient,
    *,
    user_id: Annotated[int, Field(description="Greenhouse user ID — get from list_users")],
) -> dict[str, Any]:
    """List auto-apply permission rules for a user. Read-only.

    These rules automatically grant the user a role on new jobs matching
    criteria (office, department). To find user_id: list_users → match by name.
    """
    return await client.harvest_get(f"/users/{user_id}/permissions/future_jobs")


async def add_future_job_permission(
    client: GreenhouseClient,
    *,
    user_id: Annotated[int, Field(description="Greenhouse user ID — get from list_users")],
    user_role_id: Annotated[int, Field(description="Role to auto-grant — get from list_user_roles")],
    office_id: Annotated[int | None, Field(description="Scope to jobs in this office — omit for all offices")] = None,
    department_id: Annotated[int | None, Field(description="Scope to jobs in this department — omit for all departments")] = None,
) -> dict[str, Any]:
    """Auto-grant a role on all future jobs. Write operation — admin only.

    Users say "give Sarah recruiter access to all new Engineering jobs." For
    user_id: list_users. For user_role_id: list_user_roles. Scope with
    office_id (list_offices) or department_id (list_departments).
    """
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
    user_id: Annotated[int, Field(description="Greenhouse user ID — get from list_users")],
    future_job_permission_id: Annotated[int, Field(description="Permission ID to revoke — get from list_future_job_permissions")],
) -> dict[str, Any]:
    """Revoke a future job permission rule. Write operation — admin only.

    To find user_id: list_users → match by name. For the permission ID:
    list_future_job_permissions for the user.
    """
    return await client.harvest_delete(
        f"/users/{user_id}/permissions/future_jobs/{future_job_permission_id}"
    )
