"""Harvest API — Custom Fields tools (9 tools)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_custom_fields(
    client: GreenhouseClient,
    *,
    field_type: Annotated[str | None, Field(description="Filter by type: 'candidate', 'application', 'job', 'offer', 'opening', 'rejection_question'")] = None,
) -> dict[str, Any]:
    """List all custom fields in the organization. Read-only.

    Returns field definitions (not values). Filter by field_type to see only candidate
    fields, job fields, etc. Use the returned IDs when setting custom_fields on
    create_candidate, update_candidate, or update_application. To see dropdown options
    for a field, use list_custom_field_options.
    """
    params: dict[str, Any] = {}
    if field_type is not None:
        params["field_type"] = field_type
    return await client.harvest_get("/custom_fields", params=params or None)


async def get_custom_field(
    client: GreenhouseClient,
    *,
    custom_field_id: Annotated[int, Field(description="Custom field ID — get from list_custom_fields")],
) -> dict[str, Any]:
    """Get a single custom field definition by ID. Read-only.

    Returns the field name, type, value_type, and configuration. Use list_custom_fields
    to find field IDs. For dropdown/multi-select fields, use list_custom_field_options
    to see available options.
    """
    return await client.harvest_get_one(f"/custom_fields/{custom_field_id}")


async def create_custom_field(
    client: GreenhouseClient,
    *,
    name: Annotated[str, Field(description="Display name for the custom field")],
    field_type: Annotated[str, Field(description="Where the field appears: 'candidate', 'application', 'job', 'offer', 'opening', 'rejection_question'")],
    value_type: Annotated[str, Field(description="Data type: 'short_text', 'long_text', 'yes_no', 'single_select', 'multi_select', 'currency', 'date', 'number', 'url', 'user'")],
    private: Annotated[bool, Field(description="If true, only visible to users with private field access")] = False,
    generate_email_token: Annotated[bool, Field(description="If true, generates an email token for this field")] = False,
) -> dict[str, Any]:
    """Create a new custom field definition. Write operation — admin only.

    This creates the field schema, not a value. To add dropdown options after creation,
    use create_custom_field_options. To set field values on a candidate, use
    update_candidate with custom_fields. To modify an existing field, use update_custom_field.
    """
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
    custom_field_id: Annotated[int, Field(description="Custom field ID — get from list_custom_fields")],
    name: Annotated[str | None, Field(description="New display name")] = None,
    private: Annotated[bool | None, Field(description="New privacy setting")] = None,
) -> dict[str, Any]:
    """Update a custom field's name or privacy setting. Write operation — admin only.

    Only updates the field definition, not values. To change dropdown options, use
    update_custom_field_options. To delete the field entirely, use delete_custom_field.
    """
    json_data: dict[str, Any] = {}
    if name is not None:
        json_data["name"] = name
    if private is not None:
        json_data["private"] = private
    return await client.harvest_patch(f"/custom_fields/{custom_field_id}", json_data=json_data)


async def delete_custom_field(
    client: GreenhouseClient,
    *,
    custom_field_id: Annotated[int, Field(description="Custom field ID to delete")],
) -> dict[str, Any]:
    """Delete a custom field definition and all its values. Destructive — cannot be undone.
    Admin only.

    This removes the field from all records that use it. To update the field instead,
    use update_custom_field. To remove just dropdown options, use delete_custom_field_options.
    """
    return await client.harvest_delete(f"/custom_fields/{custom_field_id}")


async def list_custom_field_options(
    client: GreenhouseClient,
    *,
    custom_field_id: Annotated[int, Field(description="Custom field ID (must be a single_select or multi_select field)")],
) -> dict[str, Any]:
    """List all dropdown options for a custom field. Read-only.

    Only applies to single_select and multi_select fields. Use the returned option IDs
    when setting custom field values. To add new options, use create_custom_field_options.
    To find custom field IDs, use list_custom_fields.
    """
    return await client.harvest_get(f"/custom_fields/{custom_field_id}/custom_field_options")


async def create_custom_field_options(
    client: GreenhouseClient,
    *,
    custom_field_id: Annotated[int, Field(description="Custom field ID (must be a single_select or multi_select field)")],
    options: Annotated[list[dict[str, Any]], Field(description="Array of {name: 'Option Label', priority: 0} — priority controls display order")],
) -> dict[str, Any]:
    """Add new dropdown options to a custom field. Write operation — admin only.

    Only applies to single_select and multi_select fields. New options are appended
    to existing ones. To update existing options, use update_custom_field_options.
    To remove options, use delete_custom_field_options.
    """
    json_data: dict[str, Any] = {"options": options}
    return await client.harvest_post(
        f"/custom_fields/{custom_field_id}/custom_field_options", json_data=json_data
    )


async def update_custom_field_options(
    client: GreenhouseClient,
    *,
    custom_field_id: Annotated[int, Field(description="Custom field ID")],
    options: Annotated[list[dict[str, Any]], Field(description="Array of {id: option_id, name: 'New Label', priority: 0} — get IDs from list_custom_field_options")],
) -> dict[str, Any]:
    """Update existing dropdown options on a custom field. Write operation — admin only.

    Changes the name or priority of existing options. To add new options, use
    create_custom_field_options. To remove options, use delete_custom_field_options.
    """
    json_data: dict[str, Any] = {"options": options}
    return await client.harvest_patch(
        f"/custom_fields/{custom_field_id}/custom_field_options", json_data=json_data
    )


async def delete_custom_field_options(
    client: GreenhouseClient,
    *,
    custom_field_id: Annotated[int, Field(description="Custom field ID")],
    option_ids: Annotated[list[int], Field(description="IDs of options to delete — get from list_custom_field_options")],
) -> dict[str, Any]:
    """Delete specific dropdown options from a custom field. Destructive — cannot be undone.
    Admin only.

    Removes the specified options. Records that had these values will show the option
    as deleted. To update options instead, use update_custom_field_options.
    """
    return await client.harvest_patch(
        f"/custom_fields/{custom_field_id}/custom_field_options",
        json_data={"option_ids": option_ids, "_destroy": True},
    )
