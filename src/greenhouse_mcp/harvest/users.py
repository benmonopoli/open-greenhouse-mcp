"""Harvest API — Users tools (8 tools)."""
from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_users(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    email: str | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
    paginate: str = "single",
) -> dict[str, Any]:
    """List all Greenhouse users, with optional filters for email and created date ranges."""
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
    user_id: int,
) -> dict[str, Any]:
    """Get a single Greenhouse user by ID."""
    return await client.harvest_get_one(f"/users/{user_id}")


async def create_user(
    client: GreenhouseClient,
    *,
    first_name: str,
    last_name: str,
    email: str,
    send_email: bool = True,
) -> dict[str, Any]:
    """Create a new Greenhouse user with first/last name and email, optionally sending an invite."""
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
    user_id: int,
    first_name: str | None = None,
    last_name: str | None = None,
) -> dict[str, Any]:
    """Update a user's first or last name."""
    json_data: dict[str, Any] = {}
    if first_name is not None:
        json_data["first_name"] = first_name
    if last_name is not None:
        json_data["last_name"] = last_name
    return await client.harvest_patch(f"/users/{user_id}", json_data=json_data)


async def disable_user(
    client: GreenhouseClient,
    *,
    user_id: int,
) -> dict[str, Any]:
    """Disable a Greenhouse user, preventing them from logging in."""
    return await client.harvest_patch(f"/users/{user_id}/disable")


async def enable_user(
    client: GreenhouseClient,
    *,
    user_id: int,
) -> dict[str, Any]:
    """Re-enable a previously disabled Greenhouse user."""
    return await client.harvest_patch(f"/users/{user_id}/enable")


async def change_user_permission_level(
    client: GreenhouseClient,
    *,
    user_id: int,
    permission_level: str,
) -> dict[str, Any]:
    """Change a user's global permission level (e.g. basic, admin, site_admin)."""
    json_data: dict[str, Any] = {"permission_level": permission_level}
    return await client.harvest_patch(
        f"/users/{user_id}/permissions/permission_level", json_data=json_data
    )


async def add_email_to_user(
    client: GreenhouseClient,
    *,
    user_id: int,
    email: str,
    send_verification: bool = True,
) -> dict[str, Any]:
    """Add an additional email address to a Greenhouse user, optionally sending verification."""
    json_data: dict[str, Any] = {"email": email, "send_verification": send_verification}
    return await client.harvest_post(f"/users/{user_id}/email_addresses", json_data=json_data)
