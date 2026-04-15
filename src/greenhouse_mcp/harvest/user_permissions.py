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
    """List all job-level permissions granted to a user. Read-only.

    Shows which jobs a user has access to and their role on each. For future job
    permissions (auto-applied to new jobs), use list_future_job_permissions. To
    grant permissions, use add_job_permission.
    """
    return await client.harvest_get(f"/users/{user_id}/permissions/jobs")


async def add_job_permission(
    client: GreenhouseClient,
    *,
    user_id: Annotated[int, Field(description="Greenhouse user ID")],
    job_id: Annotated[int, Field(description="Job to grant access to")],
    user_role_id: Annotated[int, Field(description="Role on this job — get valid IDs from list_user_roles")],
) -> dict[str, Any]:
    """Grant a user a specific role on a job. Write operation — admin only.

    This gives per-job access. For auto-applying permissions to all future jobs, use
    add_future_job_permission instead. To revoke, use remove_job_permission. Get
    role IDs from list_user_roles.
    """
    json_data: dict[str, Any] = {"job_id": job_id, "user_role_id": user_role_id}
    return await client.harvest_post(f"/users/{user_id}/permissions/jobs", json_data=json_data)


async def remove_job_permission(
    client: GreenhouseClient,
    *,
    user_id: Annotated[int, Field(description="Greenhouse user ID")],
    job_permission_id: Annotated[int, Field(description="Permission ID to revoke — get from list_job_permissions")],
) -> dict[str, Any]:
    """Revoke a user's job-level permission. Write operation — admin only.

    Get the job_permission_id from list_job_permissions. To grant permissions, use
    add_job_permission. For future job permissions, use remove_future_job_permission.
    """
    return await client.harvest_delete(
        f"/users/{user_id}/permissions/jobs/{job_permission_id}"
    )


async def list_future_job_permissions(
    client: GreenhouseClient,
    *,
    user_id: Annotated[int, Field(description="Greenhouse user ID")],
) -> dict[str, Any]:
    """List a user's future job permissions — rules that auto-apply to new jobs. Read-only.

    Future permissions automatically grant the user a role on any new job matching
    the office/department scope. For current job permissions, use list_job_permissions.
    To add future permissions, use add_future_job_permission.
    """
    return await client.harvest_get(f"/users/{user_id}/permissions/future_jobs")


async def add_future_job_permission(
    client: GreenhouseClient,
    *,
    user_id: Annotated[int, Field(description="Greenhouse user ID")],
    user_role_id: Annotated[int, Field(description="Role to auto-grant — get from list_user_roles")],
    office_id: Annotated[int | None, Field(description="Scope to jobs in this office — omit for all offices")] = None,
    department_id: Annotated[int | None, Field(description="Scope to jobs in this department — omit for all departments")] = None,
) -> dict[str, Any]:
    """Grant a user a role on all future jobs, optionally scoped to an office or department.
    Write operation — admin only.

    This creates a rule that auto-applies when new jobs are created. For one-time
    job-specific access, use add_job_permission instead. To revoke, use
    remove_future_job_permission.
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
    user_id: Annotated[int, Field(description="Greenhouse user ID")],
    future_job_permission_id: Annotated[int, Field(description="Permission ID to revoke — get from list_future_job_permissions")],
) -> dict[str, Any]:
    """Revoke a user's future job permission rule. Write operation — admin only.

    This stops the rule from applying to new jobs but does not remove permissions
    already granted to existing jobs. Get the permission_id from
    list_future_job_permissions. To add future permissions, use add_future_job_permission.
    """
    return await client.harvest_delete(
        f"/users/{user_id}/permissions/future_jobs/{future_job_permission_id}"
    )
