"""Harvest API — Users tools (8 tools)."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient, add_date_filter


async def list_users(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    cursor: Annotated[
        str | None,
        Field(description="Pass next_cursor from the previous response to get the next page"),
    ] = None,
    email: Annotated[
        str | None, Field(description="Filter by exact email address (primary or secondary)")
    ] = None,
    created_after: Annotated[
        str | None, Field(description="ISO 8601 datetime — only users created after this")
    ] = None,
    created_before: Annotated[
        str | None, Field(description="ISO 8601 datetime — only users created before this")
    ] = None,
    deactivated: Annotated[
        bool | None,
        Field(description="true = only deactivated users, false = only active; omit for both"),
    ] = None,
    paginate: Annotated[
        str, Field(description="'single' for one page, 'all' to auto-fetch every page")
    ] = "single",
) -> dict[str, Any]:
    """List all Greenhouse users (team members, not candidates). Read-only.

    This is the primary tool for resolving team member names to user IDs.
    When another tool needs a user_id (interviewer, approver, hiring manager),
    use this to find the person by name or email. Filter by email for exact
    lookup (matches the primary email first, then any secondary address), or
    paginate to scan. Each user has `deactivated` (was `disabled`),
    `primary_email`, `office_ids` and `department_ids` (get_user adds names
    and secondary emails).
    """
    params: dict[str, Any] = {"per_page": per_page}
    if cursor:
        params["cursor"] = cursor
    if email is not None:
        params["primary_email"] = email
    if deactivated is not None:
        params["deactivated"] = deactivated
    add_date_filter(params, "created_at", gt=created_after, lt=created_before)
    result = await client.harvest_get("/users", params=params, paginate=paginate)
    if email is None or cursor or client._is_error(result) or result.get("items"):
        return result
    # Not a primary address — look it up among secondary user emails.
    emails = await client.harvest_get("/user_emails", params={"email": email})
    if client._is_error(emails):
        return result
    user_ids = [e["user_id"] for e in emails.get("items", []) if e.get("user_id")]
    if not user_ids:
        return result
    params.pop("primary_email")
    params["ids"] = user_ids
    return await client.harvest_get("/users", params=params, paginate=paginate)


async def get_user(
    client: GreenhouseClient,
    *,
    user_id: Annotated[int, Field(description="Greenhouse user ID")],
) -> dict[str, Any]:
    """Get a Greenhouse user's profile by ID. Read-only.

    Returns name, primary_email, `emails` (all addresses with verified flag),
    site_admin, deactivated status, and the user's offices and departments
    (with names). To find user_id:
    list_users → match by name or email. For job-level access, see
    list_job_permissions.
    """
    user = await client.harvest_get_by_id("/users", user_id)
    if client._is_error(user):
        return user
    for key, endpoint in (("departments", "/departments"), ("offices", "/offices")):
        ids = user.get(f"{key[:-1]}_ids") or []
        if not ids:
            user[key] = []
            continue
        found = await client.harvest_get_ids(endpoint, "ids", ids)
        if not client._is_error(found):
            user[key] = [{"id": r.get("id"), "name": r.get("name")} for r in found["items"]]
    emails = await client.harvest_get("/user_emails", params={"user_ids": [user_id]})
    if not client._is_error(emails):
        user["emails"] = [
            {"email": e.get("email"), "verified": e.get("verified")}
            for e in emails.get("items", [])
        ]
    return user


async def create_user(
    client: GreenhouseClient,
    *,
    first_name: Annotated[str, Field(description="User's first name")],
    last_name: Annotated[str, Field(description="User's last name")],
    email: Annotated[str, Field(description="User's email address — must be unique in Greenhouse")],
    send_email: Annotated[
        bool, Field(description="Send an invitation email to the new user")
    ] = True,
    job_title: Annotated[str | None, Field(description="Job title on the user's profile")] = None,
    office_ids: Annotated[
        list[int] | None, Field(description="Offices to assign the user to — get from list_offices")
    ] = None,
    department_ids: Annotated[
        list[int] | None,
        Field(description="Departments to assign the user to — get from list_departments"),
    ] = None,
) -> dict[str, Any]:
    """Create a new Greenhouse user account. Write operation — admin only.

    After creating, use add_job_permission to grant access to specific jobs,
    or add_future_job_permission for automatic access to new jobs.
    """
    json_data: dict[str, Any] = {
        "first_name": first_name,
        "last_name": last_name,
        "primary_email": email,
        "send_email_invite": send_email,
    }
    if job_title is not None:
        json_data["job_title"] = job_title
    if office_ids is not None:
        json_data["office_ids"] = office_ids
    if department_ids is not None:
        json_data["department_ids"] = department_ids
    return await client.harvest_post("/users", json_data=json_data)


async def update_user(
    client: GreenhouseClient,
    *,
    user_id: Annotated[int, Field(description="Greenhouse user ID")],
    first_name: Annotated[str | None, Field(description="New first name")] = None,
    last_name: Annotated[str | None, Field(description="New last name")] = None,
    job_title: Annotated[str | None, Field(description="New job title")] = None,
    primary_email: Annotated[
        str | None,
        Field(description="New primary email — must already be a verified email on the user"),
    ] = None,
    office_ids: Annotated[
        list[int] | None, Field(description="Replace the user's offices — get from list_offices")
    ] = None,
    department_ids: Annotated[
        list[int] | None,
        Field(description="Replace the user's departments — get from list_departments"),
    ] = None,
) -> dict[str, Any]:
    """Update a user's name, title, primary email, offices or departments. Write operation.

    To find user_id: list_users → match by name or email. To make a new
    address primary, first add it with add_email_to_user and have it verified.
    """
    json_data: dict[str, Any] = {}
    for key, value in (
        ("first_name", first_name),
        ("last_name", last_name),
        ("job_title", job_title),
        ("primary_email", primary_email),
        ("office_ids", office_ids),
        ("department_ids", department_ids),
    ):
        if value is not None:
            json_data[key] = value
    return await client.harvest_patch(f"/users/{user_id}", json_data=json_data)


async def disable_user(
    client: GreenhouseClient,
    *,
    user_id: Annotated[int, Field(description="Greenhouse user ID to disable")],
) -> dict[str, Any]:
    """Deactivate (disable) a Greenhouse user, preventing login. Write operation.

    Users say "deactivate John's account." To find user_id: list_users →
    match by name or email. Can be reversed with enable_user. Returns
    {"success": true} on success.
    """
    return await client.harvest_post(f"/users/{user_id}/deactivate")


async def enable_user(
    client: GreenhouseClient,
    *,
    user_id: Annotated[int, Field(description="Greenhouse user ID to re-enable")],
) -> dict[str, Any]:
    """Re-activate (enable) a previously deactivated user. Write operation.

    To find user_id: list_users → match by name or email. Returns
    {"success": true} on success.
    """
    return await client.harvest_post(f"/users/{user_id}/activate")


async def change_user_permission_level(
    client: GreenhouseClient,
    *,
    user_id: Annotated[int, Field(description="Greenhouse user ID")],
    permission_level: Annotated[
        str,
        Field(description="Must be 'basic' — the only change Greenhouse supports via the API"),
    ] = "basic",
) -> dict[str, Any]:
    """Demote a user to Basic, revoking all their permissions. Write operation — admin only.

    Removes the user's Site Admin status and every job-level permission
    (Greenhouse "revoke permissions"). Promoting a user is not possible via
    the API — grant job roles with add_job_permission instead. To find
    user_id: list_users → match by name or email.
    """
    if permission_level.strip().lower() != "basic":
        return {
            "error": "Greenhouse only supports demoting a user to 'basic' (revoking all "
            "permissions). Use add_job_permission or add_future_job_permission to grant access.",
            "status_code": 422,
        }
    return await client.harvest_post(f"/users/{user_id}/revoke_permissions")


async def add_email_to_user(
    client: GreenhouseClient,
    *,
    user_id: Annotated[int, Field(description="Greenhouse user ID")],
    email: Annotated[str, Field(description="Email address to add")],
    send_verification: Annotated[
        bool, Field(description="Send a verification email to the new address")
    ] = True,
) -> dict[str, Any]:
    """Add a secondary email address to a Greenhouse user. Write operation.

    To find user_id: list_users → match by name or email. The address stays
    unverified until the user confirms it.
    """
    json_data: dict[str, Any] = {
        "user_id": user_id,
        "email": email,
        "send_verification": send_verification,
    }
    return await client.harvest_post("/user_emails", json_data=json_data)
