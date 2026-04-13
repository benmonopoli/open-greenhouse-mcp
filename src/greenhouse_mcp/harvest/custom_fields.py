"""Harvest API — Custom Fields tools (9 tools)."""
from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_custom_fields(
    client: GreenhouseClient,
    *,
    field_type: str | None = None,
) -> dict[str, Any]:
    """List all custom fields, optionally filtered by field_type (candidate, job, etc)."""
    params: dict[str, Any] = {}
    if field_type is not None:
        params["field_type"] = field_type
    return await client.harvest_get("/custom_fields", params=params or None)


async def get_custom_field(
    client: GreenhouseClient,
    *,
    custom_field_id: int,
) -> dict[str, Any]:
    """Get a single custom field by ID."""
    return await client.harvest_get_one(f"/custom_fields/{custom_field_id}")


async def create_custom_field(
    client: GreenhouseClient,
    *,
    name: str,
    field_type: str,
    value_type: str,
    private: bool = False,
    generate_email_token: bool = False,
) -> dict[str, Any]:
    """Create a new custom field with name, field_type, and value_type."""
    json_data: dict[str, Any] = {
        "name": name,
        "field_type": field_type,
        "value_type": value_type,
        "private": private,
        "generate_email_token": generate_email_token,
    }
    return await client.harvest_post("/custom_fields", json_data=json_data)


async def update_custom_field(
    client: GreenhouseClient,
    *,
    custom_field_id: int,
    name: str | None = None,
    private: bool | None = None,
) -> dict[str, Any]:
    """Update a custom field's name or privacy setting."""
    json_data: dict[str, Any] = {}
    if name is not None:
        json_data["name"] = name
    if private is not None:
        json_data["private"] = private
    return await client.harvest_patch(f"/custom_fields/{custom_field_id}", json_data=json_data)


async def delete_custom_field(
    client: GreenhouseClient,
    *,
    custom_field_id: int,
) -> dict[str, Any]:
    """Delete a custom field by ID."""
    return await client.harvest_delete(f"/custom_fields/{custom_field_id}")


async def list_custom_field_options(
    client: GreenhouseClient,
    *,
    custom_field_id: int,
) -> dict[str, Any]:
    """List all options for a dropdown/multi-select custom field."""
    return await client.harvest_get(f"/custom_fields/{custom_field_id}/custom_field_options")


async def create_custom_field_options(
    client: GreenhouseClient,
    *,
    custom_field_id: int,
    options: list[dict[str, Any]],
) -> dict[str, Any]:
    """Add new options to a dropdown/multi-select custom field."""
    json_data: dict[str, Any] = {"options": options}
    return await client.harvest_post(
        f"/custom_fields/{custom_field_id}/custom_field_options", json_data=json_data
    )


async def update_custom_field_options(
    client: GreenhouseClient,
    *,
    custom_field_id: int,
    options: list[dict[str, Any]],
) -> dict[str, Any]:
    """Update existing options on a dropdown/multi-select custom field."""
    json_data: dict[str, Any] = {"options": options}
    return await client.harvest_patch(
        f"/custom_fields/{custom_field_id}/custom_field_options", json_data=json_data
    )


async def delete_custom_field_options(
    client: GreenhouseClient,
    *,
    custom_field_id: int,
    option_ids: list[int],
) -> dict[str, Any]:
    """Delete specific options from a dropdown/multi-select custom field by option IDs."""
    return await client.harvest_patch(
        f"/custom_fields/{custom_field_id}/custom_field_options",
        json_data={"option_ids": option_ids, "_destroy": True},
    )
