"""User permission resolution from Greenhouse API."""

from __future__ import annotations

from dataclasses import dataclass

from greenhouse_mcp.client import GreenhouseClient


@dataclass(frozen=True)
class UserPermissions:
    """Resolved permissions for a Greenhouse user."""

    user_id: int
    name: str
    email: str
    site_admin: bool
    disabled: bool
    profile: str  # "full", "recruiter", or "read-only"
    permitted_job_ids: set[int] | None  # None = all jobs (site admin)


async def resolve_user_permissions(
    client: GreenhouseClient,
    *,
    user_id: int,
) -> UserPermissions:
    """Fetch a user from Greenhouse and derive their MCP permissions.

    Raises ValueError if the user is not found or is disabled.
    """
    user = await client.harvest_get_one(f"/users/{user_id}")

    if GreenhouseClient._is_error(user):
        raise ValueError(
            f"Cannot resolve user {user_id}: {user.get('error', 'Unknown error')}. "
            f"Check that GREENHOUSE_USER_ID is a valid Greenhouse user ID."
        )

    if user.get("disabled", False):
        raise ValueError(
            f"User {user_id} ({user.get('name', 'unknown')}) is disabled in Greenhouse. "
            f"Cannot start MCP server for a disabled user."
        )

    is_admin = user.get("site_admin", False)

    if is_admin:
        return UserPermissions(
            user_id=user_id,
            name=user.get("name", ""),
            email=user.get("primary_email_address", ""),
            site_admin=True,
            disabled=False,
            profile="full",
            permitted_job_ids=None,
        )

    # Non-admin: fetch job permissions
    job_perms = await client.harvest_get(f"/users/{user_id}/permissions/jobs", paginate="all")
    items = job_perms.get("items", [])
    job_ids = {item["job_id"] for item in items if "job_id" in item}

    if job_ids:
        return UserPermissions(
            user_id=user_id,
            name=user.get("name", ""),
            email=user.get("primary_email_address", ""),
            site_admin=False,
            disabled=False,
            profile="recruiter",
            permitted_job_ids=job_ids,
        )

    return UserPermissions(
        user_id=user_id,
        name=user.get("name", ""),
        email=user.get("primary_email_address", ""),
        site_admin=False,
        disabled=False,
        profile="read-only",
        permitted_job_ids=set(),
    )
