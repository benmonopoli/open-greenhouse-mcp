"""Harvest API — Users tools (8 tools)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_users(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    page: Annotated[int, Field(description="Page number (starts at 1)")] = 1,
    email: Annotated[str | None, Field(description="Filter by exact email address")] = None,
    created_after: Annotated[str | None, Field(description="ISO 8601 datetime — only users created after this")] = None,
    created_before: Annotated[str | None, Field(description="ISO 8601 datetime — only users created before this")] = None,
    paginate: Annotated[str, Field(description="'single' for one page, 'all' to auto-fetch every page")] = "single",
) -> dict[str, Any]:
    """List all Greenhouse users (team members, not candidates). Read-only.

    Users are people who log into Greenhouse — recruiters, hiring managers, admins.
    Filter by email to find a specific user. For candidates (applicants), use
    list_candidates instead. User IDs are needed for interviewer assignments,
    prospect ownership, and permission management.
    """
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    if email is not None:
        params["email"] = email
    if created_after is not None:
        params["created_after"] = created_after
    if created_before is not None:
        params["created_before"] = created_before
    return await client.harvest_get("/users", params=params, paginate=paginate)


async def get_user(
    client: GreenhouseClient,
    *,
    user_id: Annotated[int, Field(description="Greenhouse user ID")],
) -> dict[str, Any]:
    """Get a single Greenhouse user by ID. Read-only. Returns the user's name, email,
    permission level, and status (active/disabled).

    Use list_users with email filter to find a user by email. For a user's job-level
    permissions, use list_job_permissions. User IDs appear throughout the API as
    interviewer_ids, prospect_owner_id, etc.
    """
    return await client.harvest_get_one(f"/users/{user_id}")


async def create_user(
    client: GreenhouseClient,
    *,
    first_name: Annotated[str, Field(description="User's first name")],
    last_name: Annotated[str, Field(description="User's last name")],
    email: Annotated[str, Field(description="User's email address — must be unique in Greenhouse")],
    send_email: Annotated[bool, Field(description="Send an invitation email to the new user")] = True,
) -> dict[str, Any]:
    """Create a new Greenhouse user account. Write operation — admin only.

    Creates a team member account (not a candidate). Set send_email=false to create
    the account without notifying the user. To modify permissions after creation,
    use change_user_permission_level and add_job_permission. To disable an account,
    use disable_user.
    """
    json_data: dict[str, Any] = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "send_email": send_email,
    }
    return await client.harvest_post("/users", json_data=json_data)


async def update_user(
    client: GreenhouseClient,
    *,
    user_id: Annotated[int, Field(description="Greenhouse user ID")],
    first_name: Annotated[str | None, Field(description="New first name")] = None,
    last_name: Annotated[str | None, Field(description="New last name")] = None,
) -> dict[str, Any]:
    """Update a user's first or last name. Write operation.

    Only name changes are supported. To change permissions, use
    change_user_permission_level. To add emails, use add_email_to_user.
    To disable the account, use disable_user.
    """
    json_data: dict[str, Any] = {}
    if first_name is not None:
        json_data["first_name"] = first_name
    if last_name is not None:
        json_data["last_name"] = last_name
    return await client.harvest_patch(f"/users/{user_id}", json_data=json_data)


async def disable_user(
    client: GreenhouseClient,
    *,
    user_id: Annotated[int, Field(description="Greenhouse user ID to disable")],
) -> dict[str, Any]:
    """Disable a Greenhouse user, preventing them from logging in. Write operation.

    The user's data and permissions are preserved but they cannot access Greenhouse.
    Can be reversed with enable_user. For permanent removal, this is the recommended
    approach — Greenhouse does not support user deletion.
    """
    return await client.harvest_patch(f"/users/{user_id}/disable")


async def enable_user(
    client: GreenhouseClient,
    *,
    user_id: Annotated[int, Field(description="Greenhouse user ID to re-enable")],
) -> dict[str, Any]:
    """Re-enable a previously disabled Greenhouse user. Write operation.

    Restores login access. Their permissions and data are preserved from before
    disabling. To disable a user, use disable_user.
    """
    return await client.harvest_patch(f"/users/{user_id}/enable")


async def change_user_permission_level(
    client: GreenhouseClient,
    *,
    user_id: Annotated[int, Field(description="Greenhouse user ID")],
    permission_level: Annotated[str, Field(description="New level — get valid values from list_user_roles")],
) -> dict[str, Any]:
    """Change a user's global permission level. Write operation — admin only.

    Permission levels control what the user can do across Greenhouse (e.g. basic user,
    job admin, site admin). Get valid permission levels from list_user_roles. For
    job-specific permissions, use add_job_permission instead.
    """
    json_data: dict[str, Any] = {"permission_level": permission_level}
    return await client.harvest_patch(
        f"/users/{user_id}/permissions/permission_level", json_data=json_data
    )


async def add_email_to_user(
    client: GreenhouseClient,
    *,
    user_id: Annotated[int, Field(description="Greenhouse user ID")],
    email: Annotated[str, Field(description="Email address to add")],
    send_verification: Annotated[bool, Field(description="Send a verification email to the new address")] = True,
) -> dict[str, Any]:
    """Add an additional email address to a Greenhouse user. Write operation.

    Users can have multiple email addresses. Set send_verification=false to skip the
    verification email. To update a user's name, use update_user.
    """
    json_data: dict[str, Any] = {"email": email, "send_verification": send_verification}
    return await client.harvest_post(f"/users/{user_id}/email_addresses", json_data=json_data)
