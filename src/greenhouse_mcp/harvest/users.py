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
    created_after: Annotated[
        str | None, Field(description="ISO 8601 datetime — only users created after this")
    ] = None,
    created_before: Annotated[
        str | None, Field(description="ISO 8601 datetime — only users created before this")
    ] = None,
    paginate: Annotated[
        str, Field(description="'single' for one page, 'all' to auto-fetch every page")
    ] = "single",
) -> dict[str, Any]:
    """List all Greenhouse users (team members, not candidates). Read-only.

    This is the primary tool for resolving team member names to user IDs.
    When another tool needs a user_id (interviewer, approver, hiring manager),
    use this to find the person by name or email. Filter by email for exact
    lookup, or paginate to scan.
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
    """Get a Greenhouse user's profile by ID. Read-only.

    Returns name, email, permission level, and active/disabled status. To find
    user_id: list_users → match by name or email.
    """
    return await client.harvest_get_one(f"/users/{user_id}")


async def create_user(
    client: GreenhouseClient,
    *,
    first_name: Annotated[str, Field(description="User's first name")],
    last_name: Annotated[str, Field(description="User's last name")],
    email: Annotated[str, Field(description="User's email address — must be unique in Greenhouse")],
    send_email: Annotated[
        bool, Field(description="Send an invitation email to the new user")
    ] = True,
) -> dict[str, Any]:
    """Create a new Greenhouse user account. Write operation — admin only.

    After creating, use add_job_permission to grant access to specific jobs,
    or add_future_job_permission for automatic access to new jobs.
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
    """Update a user's name. Write operation.

    To find user_id: list_users → match by name or email.
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
    """Disable a Greenhouse user, preventing login. Write operation.

    Users say "deactivate John's account." To find user_id: list_users →
    match by name or email. Can be reversed with enable_user.
    """
    return await client.harvest_patch(f"/users/{user_id}/disable")


async def enable_user(
    client: GreenhouseClient,
    *,
    user_id: Annotated[int, Field(description="Greenhouse user ID to re-enable")],
) -> dict[str, Any]:
    """Re-enable a previously disabled user. Write operation.

    To find user_id: list_users → match by name or email.
    """
    return await client.harvest_patch(f"/users/{user_id}/enable")


async def change_user_permission_level(
    client: GreenhouseClient,
    *,
    user_id: Annotated[int, Field(description="Greenhouse user ID")],
    permission_level: Annotated[
        str, Field(description="New level — get valid values from list_user_roles")
    ],
) -> dict[str, Any]:
    """Change a user's global permission level. Write operation — admin only.

    To find user_id: list_users → match by name or email.
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
    send_verification: Annotated[
        bool, Field(description="Send a verification email to the new address")
    ] = True,
) -> dict[str, Any]:
    """Add an email address to a Greenhouse user. Write operation.

    To find user_id: list_users → match by name or email.
    """
    json_data: dict[str, Any] = {"email": email, "send_verification": send_verification}
    return await client.harvest_post(f"/users/{user_id}/email_addresses", json_data=json_data)
