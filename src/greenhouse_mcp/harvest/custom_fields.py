"""Harvest API — Custom Fields tools (9 tools)."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_custom_fields(
    client: GreenhouseClient,
    *,
    field_type: Annotated[
        str | None,
        Field(
            description="Filter: candidate, application, job, offer, opening, rejection_question"
        ),
    ] = None,
) -> dict[str, Any]:
    """List all custom field definitions. Read-only.

    Resolves custom field names to IDs. When a user mentions a custom field
    by name, use this to find its ID for update_candidate, update_application,
    or update_current_offer. Filter by field_type to narrow results.
    """
    params: dict[str, Any] = {}
    if field_type is not None:
        params["field_type"] = field_type
    return await client.harvest_get("/custom_fields", params=params or None)


async def get_custom_field(
    client: GreenhouseClient,
    *,
    custom_field_id: Annotated[
        int, Field(description="Custom field ID — get from list_custom_fields")
    ],
) -> dict[str, Any]:
    """Get a custom field definition by ID. Read-only.

    Returns field name, type, value type, and configuration.
    To find custom_field_id: list_custom_fields → match by name.
    """
    return await client.harvest_get_one(f"/custom_fields/{custom_field_id}")


async def create_custom_field(
    client: GreenhouseClient,
    *,
    name: Annotated[str, Field(description="Display name for the custom field")],
    field_type: Annotated[
        str,
        Field(
            description="Entity: candidate, application, job, offer, opening, rejection_question"
        ),
    ],
    value_type: Annotated[
        str,
        Field(
            description="short_text, long_text, yes_no, single/multi_select, currency, date, number"
        ),
    ],
    private: Annotated[
        bool, Field(description="If true, only visible to users with private field access")
    ] = False,
    generate_email_token: Annotated[
        bool, Field(description="If true, generates an email token for this field")
    ] = False,
) -> dict[str, Any]:
    """Create a new custom field definition. Write operation — admin only.

    Defines a new field available on candidates, applications, jobs, or offers.
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
    custom_field_id: Annotated[
        int, Field(description="Custom field ID — get from list_custom_fields")
    ],
    name: Annotated[str | None, Field(description="New display name")] = None,
    private: Annotated[bool | None, Field(description="New privacy setting")] = None,
) -> dict[str, Any]:
    """Update a custom field's name or privacy. Write operation — admin only.

    To find custom_field_id: list_custom_fields → match by name.
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
    """Delete a custom field and all its values. Destructive — cannot be undone. Admin only.

    To find custom_field_id: list_custom_fields → match by name.
    """
    return await client.harvest_delete(f"/custom_fields/{custom_field_id}")


async def list_custom_field_options(
    client: GreenhouseClient,
    *,
    custom_field_id: Annotated[
        int, Field(description="Custom field ID (must be a single_select or multi_select field)")
    ],
) -> dict[str, Any]:
    """List dropdown options for a custom field. Read-only.

    To find custom_field_id: list_custom_fields → match by name.
    """
    return await client.harvest_get(f"/custom_fields/{custom_field_id}/custom_field_options")


async def create_custom_field_options(
    client: GreenhouseClient,
    *,
    custom_field_id: Annotated[
        int, Field(description="Custom field ID (must be a single_select or multi_select field)")
    ],
    options: Annotated[
        list[dict[str, Any]],
        Field(
            description="Array of {name, priority} — priority controls display order"
        ),
    ],
) -> dict[str, Any]:
    """Add dropdown options to a custom field. Write operation — admin only.

    To find custom_field_id: list_custom_fields → match by name.
    """
    json_data: dict[str, Any] = {"options": options}
    return await client.harvest_post(
        f"/custom_fields/{custom_field_id}/custom_field_options", json_data=json_data
    )


async def update_custom_field_options(
    client: GreenhouseClient,
    *,
    custom_field_id: Annotated[int, Field(description="Custom field ID")],
    options: Annotated[
        list[dict[str, Any]],
        Field(
            description="Array of {id, name, priority} — get IDs from list_custom_field_options"
        ),
    ],
) -> dict[str, Any]:
    """Update dropdown options on a custom field. Write operation — admin only.

    To find custom_field_id: list_custom_fields → match by name. For
    option IDs: list_custom_field_options → match by name.
    """
    json_data: dict[str, Any] = {"options": options}
    return await client.harvest_patch(
        f"/custom_fields/{custom_field_id}/custom_field_options", json_data=json_data
    )


async def delete_custom_field_options(
    client: GreenhouseClient,
    *,
    custom_field_id: Annotated[int, Field(description="Custom field ID")],
    option_ids: Annotated[
        list[int],
        Field(description="IDs of options to delete — get from list_custom_field_options"),
    ],
) -> dict[str, Any]:
    """Delete dropdown options from a custom field. Destructive — cannot be undone. Admin only.

    To find custom_field_id: list_custom_fields → match by name. For
    option IDs: list_custom_field_options → match by name.
    """
    return await client.harvest_patch(
        f"/custom_fields/{custom_field_id}/custom_field_options",
        json_data={"option_ids": option_ids, "_destroy": True},
    )
