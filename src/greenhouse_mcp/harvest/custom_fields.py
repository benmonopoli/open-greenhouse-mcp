"""Harvest API — Custom Fields tools (9 tools)."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient

# Up to this many options are written one call at a time (synchronous, returns the
# created/updated rows). Larger batches use Greenhouse's asynchronous bulk endpoint.
_BULK_THRESHOLD = 50


def _option_payload(option: dict[str, Any], default_order: int | None) -> dict[str, Any]:
    """Map a caller's option dict ({name, priority|sort_order, external_id}) to v3 shape."""
    out: dict[str, Any] = {}
    if "name" in option:
        out["name"] = option["name"]
    order = option.get("sort_order", option.get("priority"))
    if order is None:
        order = default_order
    if order is not None:
        out["sort_order"] = order
    if option.get("external_id") is not None:
        out["external_id"] = option["external_id"]
    return out


def _bulk_note(result: dict[str, Any], count: int) -> dict[str, Any]:
    if not GreenhouseClient._is_error(result):
        result["note"] = (
            f"{count} options submitted as an asynchronous Greenhouse bulk request; "
            "track it with get_bulk_request_status(bulk_action_uuid) or check "
            "list_custom_field_options in a minute."
        )
    return result


async def list_custom_fields(
    client: GreenhouseClient,
    *,
    field_type: Annotated[
        str | None,
        Field(
            description="Filter: candidate, application, job, offer, opening, "
            "rejection_question, referral_question, user_attribute"
        ),
    ] = None,
    active: Annotated[
        bool | None, Field(description="true = live fields only, false = archived only")
    ] = None,
) -> dict[str, Any]:
    """List all custom field definitions. Read-only.

    Resolves custom field names to IDs. When a user mentions a custom field
    by name, use this to find its ID (or `name_key`) for update_candidate,
    update_application, or update_current_offer. Filter by field_type to
    narrow results. Dropdown options are separate: list_custom_field_options.
    """
    params: dict[str, Any] = {"per_page": 500}
    if field_type is not None:
        params["field_type"] = field_type
    if active is not None:
        params["active"] = active
    return await client.harvest_get("/custom_fields", params=params, paginate="all")


async def get_custom_field(
    client: GreenhouseClient,
    *,
    custom_field_id: Annotated[
        int, Field(description="Custom field ID — get from list_custom_fields")
    ],
) -> dict[str, Any]:
    """Get a custom field definition by ID. Read-only.

    Returns field name, name_key, field type, value type, and configuration.
    For single/multi-select fields, `custom_field_options` lists the
    dropdown options. To find custom_field_id: list_custom_fields → match by name.
    """
    field = await client.harvest_get_by_id("/custom_fields", custom_field_id)
    if client._is_error(field):
        return field
    if field.get("value_type") in ("single_select", "multi_select"):
        options = await client.harvest_get(
            "/custom_field_options",
            params={"custom_field_ids": [custom_field_id], "per_page": 500},
            paginate="all",
        )
        if not client._is_error(options):
            field["custom_field_options"] = sorted(
                options.get("items", []), key=lambda o: o.get("sort_order") or 0
            )
    return field


async def create_custom_field(
    client: GreenhouseClient,
    *,
    name: Annotated[str, Field(description="Display name for the custom field")],
    field_type: Annotated[
        str,
        Field(
            description="Entity: candidate, application, job, offer, opening, user_attribute"
        ),
    ],
    value_type: Annotated[
        str,
        Field(
            description="short_text, long_text, yes_no, single/multi_select, currency, date, "
            "number, url, user, currency_range, number_range"
        ),
    ],
    private: Annotated[
        bool, Field(description="If true, only visible to users with private field access")
    ] = False,
    generate_email_token: Annotated[
        bool, Field(description="If true, generates an email token for this field")
    ] = False,
    description: Annotated[
        str | None, Field(description="Helper text shown beneath the field label")
    ] = None,
    options: Annotated[
        list[dict[str, Any]] | None,
        Field(description="Initial dropdown options for select fields: [{name, sort_order}]"),
    ] = None,
) -> dict[str, Any]:
    """Create a new custom field definition. Write operation — admin only.

    Defines a new field available on candidates, applications, jobs, offers,
    openings or users.
    """
    json_data: dict[str, Any] = {
        "name": name,
        "field_type": field_type,
        "value_type": value_type,
        "private": private,
        "generate_email_token": generate_email_token,
    }
    if description is not None:
        json_data["description"] = description
    if options:
        json_data["custom_field_options"] = [
            _option_payload(o, i) for i, o in enumerate(options)
        ]
    return await client.harvest_post("/custom_fields", json_data=json_data)


async def update_custom_field(
    client: GreenhouseClient,
    *,
    custom_field_id: Annotated[
        int, Field(description="Custom field ID — get from list_custom_fields")
    ],
    name: Annotated[str | None, Field(description="New display name")] = None,
    private: Annotated[bool | None, Field(description="New privacy setting")] = None,
    description: Annotated[str | None, Field(description="New helper text")] = None,
) -> dict[str, Any]:
    """Update a custom field's name, privacy or description. Write operation — admin only.

    To find custom_field_id: list_custom_fields → match by name. Renaming
    does not change the field's name_key.
    """
    json_data: dict[str, Any] = {}
    if name is not None:
        json_data["name"] = name
    if private is not None:
        json_data["private"] = private
    if description is not None:
        json_data["description"] = description
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
    active: Annotated[
        bool | None, Field(description="true = selectable options only, false = archived only")
    ] = None,
) -> dict[str, Any]:
    """List dropdown options for a custom field. Read-only.

    To find custom_field_id: list_custom_fields → match by name. Options
    have `sort_order` (was `priority`) and are returned in that order.
    """
    params: dict[str, Any] = {"custom_field_ids": [custom_field_id], "per_page": 500}
    if active is not None:
        params["active"] = active
    result = await client.harvest_get("/custom_field_options", params=params, paginate="all")
    if not client._is_error(result):
        result["items"].sort(key=lambda o: o.get("sort_order") or 0)
    return result


async def create_custom_field_options(
    client: GreenhouseClient,
    *,
    custom_field_id: Annotated[
        int, Field(description="Custom field ID (must be a single_select or multi_select field)")
    ],
    options: Annotated[
        list[dict[str, Any]],
        Field(
            description="Array of {name, sort_order, external_id?} — sort_order (or legacy "
            "priority) controls display order; defaults to list position"
        ),
    ],
) -> dict[str, Any]:
    """Add dropdown options to a custom field. Write operation — admin only.

    To find custom_field_id: list_custom_fields → match by name. Up to 50
    options are created immediately and returned; larger lists are sent as
    an asynchronous Greenhouse bulk request.
    """
    rows = [
        {**_option_payload(o, i), "custom_field_id": custom_field_id}
        for i, o in enumerate(options)
    ]
    if len(rows) > _BULK_THRESHOLD:
        result = await client.harvest_post("/custom_field_options/bulk", json_data={"data": rows})
        return _bulk_note(result, len(rows))
    created: list[Any] = []
    errors: list[Any] = []
    for row in rows:
        res = await client.harvest_post("/custom_field_options", json_data=row)
        if client._is_error(res):
            errors.append({"option": row, "error": res})
        else:
            created.append(res)
    return _write_summary("created", created, errors)


async def update_custom_field_options(
    client: GreenhouseClient,
    *,
    custom_field_id: Annotated[int, Field(description="Custom field ID")],
    options: Annotated[
        list[dict[str, Any]],
        Field(
            description="Array of {id, name?, sort_order?, external_id?} — get IDs from "
            "list_custom_field_options"
        ),
    ],
) -> dict[str, Any]:
    """Update dropdown options on a custom field. Write operation — admin only.

    To find custom_field_id: list_custom_fields → match by name. For
    option IDs: list_custom_field_options → match by name. Up to 50 options
    are updated immediately; larger lists use an asynchronous bulk request.
    """
    missing = [o for o in options if o.get("id") is None]
    if missing:
        return {"error": "Every option needs an 'id' — get IDs from list_custom_field_options.",
                "status_code": 422, "detail": missing}
    rows = [{**_option_payload(o, None), "id": o["id"]} for o in options]
    if len(rows) > _BULK_THRESHOLD:
        result = await client.harvest_patch(
            "/custom_field_options/bulk", json_data={"data": rows}
        )
        return _bulk_note(result, len(rows))
    updated: list[Any] = []
    errors: list[Any] = []
    for row in rows:
        body = {k: v for k, v in row.items() if k != "id"}
        res = await client.harvest_patch(f"/custom_field_options/{row['id']}", json_data=body)
        if client._is_error(res):
            errors.append({"option_id": row["id"], "error": res})
        else:
            updated.append(res)
    return _write_summary("updated", updated, errors)


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
    option IDs: list_custom_field_options → match by name. Historical
    selections keep the (now inactive) option. Up to 50 options are deleted
    immediately; larger lists use an asynchronous bulk request.
    """
    if len(option_ids) > _BULK_THRESHOLD:
        result = await client.harvest_delete(
            "/custom_field_options/bulk", json_data={"data": list(option_ids)}
        )
        return _bulk_note(result, len(option_ids))
    deleted: list[Any] = []
    errors: list[Any] = []
    for option_id in option_ids:
        res = await client.harvest_delete(f"/custom_field_options/{option_id}")
        if client._is_error(res):
            errors.append({"option_id": option_id, "error": res})
        else:
            deleted.append(option_id)
    return _write_summary("deleted", deleted, errors)


def _write_summary(verb: str, done: list[Any], errors: list[Any]) -> dict[str, Any]:
    """Summarise per-item writes; an all-failed batch is returned as an error dict."""
    if errors and not done:
        first = errors[0].get("error", {})
        return {
            "error": f"No options were {verb}.",
            "status_code": first.get("status_code", 422),
            "detail": errors,
        }
    out: dict[str, Any] = {verb: done, "count": len(done)}
    if errors:
        out["errors"] = errors
    return out
