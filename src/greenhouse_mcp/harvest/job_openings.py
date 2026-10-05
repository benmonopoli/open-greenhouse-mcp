"""Harvest API — Job Openings tools (9 tools).

v3 openings live at ``/v3/openings`` (filtered by ``job_ids``) and report ``open``
(boolean) instead of v1's ``status`` string.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient
from greenhouse_mcp.harvest._custom_field_merge import merged_custom_fields
from greenhouse_mcp.harvest.jobs import _v3_custom_fields


def _with_status(opening: dict[str, Any]) -> dict[str, Any]:
    """Add the v1-style ``status`` ('open'/'closed') derived from v3's ``open`` flag."""
    if "open" in opening and "status" not in opening:
        opening["status"] = "open" if opening["open"] else "closed"
    return opening


async def list_job_openings(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    status: Annotated[str | None, Field(description="Filter by status: 'open' or 'closed'")] = None,
) -> dict[str, Any]:
    """List openings (headcount) for a job. Read-only.

    An opening represents one position to fill — a job can have multiple.
    Each opening has id, opening_id (external ID), open (bool) and status
    ('open'/'closed'), close_reason_id, application_id (the hire, if filled),
    target_start_on, and custom_fields. To find job_id: list_jobs → match by name.
    """
    params: dict[str, Any] = {"job_ids": [job_id], "per_page": 500}
    if status is not None:
        if status not in ("open", "closed"):
            return {"error": "status must be 'open' or 'closed'", "status_code": 422}
        params["open"] = status == "open"
    result = await client.harvest_get("/openings", params=params, paginate="all")
    if client._is_error(result):
        return result
    items = sorted(result.get("items", []), key=lambda o: (o.get("sort_order") or 0))
    result["items"] = [_with_status(o) for o in items]
    return result


async def get_job_opening(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    opening_id: Annotated[
        int, Field(description="Opening ID within the job — get from list_job_openings")
    ],
) -> dict[str, Any]:
    """Get a specific opening on a job. Read-only.

    Returns open/status, close_reason_id, custom fields, and the hired
    application_id if filled. To find job_id: list_jobs → match by name. To
    find opening_id: list_job_openings on the job.
    """
    opening = await client.harvest_get_by_id("/openings", opening_id)
    if client._is_error(opening):
        return opening
    if opening.get("job_id") != job_id:
        return client._error_dict(
            404, {"message": f"Opening {opening_id} does not belong to job {job_id}"}
        )
    return _with_status(opening)


async def create_job_opening(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    opening_id: Annotated[
        str | None, Field(description="Custom external opening identifier (not the Greenhouse ID)")
    ] = None,
    status: Annotated[
        str | None, Field(description="Initial status: 'open' (default) or 'closed'")
    ] = None,
    close_reason_id: Annotated[
        int | None, Field(description="If closing immediately — get from list_close_reasons")
    ] = None,
    custom_fields: Annotated[
        list[dict[str, Any]] | None, Field(
            description="Array of {id, value} (or {custom_field_id, value}) — get field IDs "
            "from list_custom_fields"
        ),
    ] = None,
) -> dict[str, Any]:
    """Add a new headcount to a job. Write operation.

    Users say "add another opening to the Backend role." To find job_id:
    list_jobs → match by name. Openings are created open; with
    status='closed' the new opening is closed straight after (with
    close_reason_id if given).
    """
    json_data: dict[str, Any] = {"job_id": job_id}
    if opening_id is not None:
        json_data["opening_id"] = opening_id
    if custom_fields is not None:
        json_data["custom_fields"] = _v3_custom_fields(custom_fields)
    created = await client.harvest_post("/openings", json_data=json_data)
    if client._is_error(created) or status != "closed":
        return created
    close: dict[str, Any] = {"job_id": job_id, "status": "closed"}
    if close_reason_id is not None:
        close["close_reason_id"] = close_reason_id
    closed = await client.harvest_patch(f"/openings/{created['id']}", json_data=close)
    if client._is_error(closed):
        return {**created, "close_error": closed}
    return closed


async def update_job_opening(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    opening_id: Annotated[int, Field(description="Opening ID within the job")],
    status: Annotated[str | None, Field(description="New status: 'open' or 'closed'")] = None,
    close_reason_id: Annotated[
        int | None, Field(description="Reason for closing — get from list_close_reasons")
    ] = None,
    external_opening_id: Annotated[
        str | None, Field(description="New custom external opening identifier")
    ] = None,
    target_start_on: Annotated[
        str | None, Field(description="Target start date as 'YYYY-MM-DD'")
    ] = None,
    custom_fields: Annotated[
        list[dict[str, Any]] | None, Field(
            description="Array of {id, value} (or {custom_field_id, value}) — get field IDs "
            "from list_custom_fields"
        ),
    ] = None,
) -> dict[str, Any]:
    """Update a job opening's status, target start date, or custom fields. Write operation.

    To find job_id: list_jobs → match by name. To find opening_id: list_job_openings on the job.
    For close_reason_id: list_close_reasons → match by name. Closing a job's
    last open opening closes the job.
    """
    json_data: dict[str, Any] = {"job_id": job_id}
    optional = {
        "status": status,
        "close_reason_id": close_reason_id,
        "opening_id": external_opening_id,
        "target_start_on": target_start_on,
    }
    json_data.update({k: v for k, v in optional.items() if v is not None})
    if custom_fields is not None:
        # v3 replaces the whole collection: send current values plus this change.
        merged = await merged_custom_fields(client, "/openings", opening_id, custom_fields)
        if client._is_error(merged):
            return merged  # type: ignore[return-value]
        json_data["custom_fields"] = merged
    return await client.harvest_patch(f"/openings/{opening_id}", json_data=json_data)


async def delete_job_opening(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    opening_id: Annotated[int, Field(description="Opening ID to delete")],
) -> dict[str, Any]:
    """Delete a job opening. Destructive — cannot be undone.

    To find job_id: list_jobs → match by name. To find opening_id: list_job_openings on the job.
    """
    opening = await client.harvest_get_by_id("/openings", opening_id)
    if client._is_error(opening):
        return opening
    if opening.get("job_id") != job_id:
        return client._error_dict(
            404, {"message": f"Opening {opening_id} does not belong to job {job_id}"}
        )
    return await client.harvest_delete(f"/openings/{opening_id}")


async def bulk_create_job_openings(
    client: GreenhouseClient,
    *,
    openings: Annotated[
        list[dict[str, Any]],
        Field(
            description="Array of {job_id (required), opening_id (external ID, optional), "
            "custom_fields (optional)}"
        ),
    ],
    callback_url: Annotated[
        str | None, Field(description="Optional HTTPS URL Greenhouse POSTs to when done")
    ] = None,
) -> dict[str, Any]:
    """Create many openings in one asynchronous request. Write operation — admin only.

    Returns bulk_action_uuid and status; check progress with
    get_bulk_request_status. For one opening use create_job_opening.
    """
    data = []
    for item in openings:
        entry = dict(item)
        if "custom_fields" in entry:
            entry["custom_fields"] = _v3_custom_fields(entry["custom_fields"])
        data.append(entry)
    body: dict[str, Any] = {"data": data}
    if callback_url is not None:
        body["callback_url"] = callback_url
    return await client.harvest_post("/openings/bulk", json_data=body)


async def bulk_update_job_openings(
    client: GreenhouseClient,
    *,
    openings: Annotated[
        list[dict[str, Any]],
        Field(
            description="Array of {id (Greenhouse opening ID, required), status ('open'/"
            "'closed'), close_reason_id, opening_id (external ID), target_start_on, "
            "custom_fields}"
        ),
    ],
    callback_url: Annotated[
        str | None, Field(description="Optional HTTPS URL Greenhouse POSTs to when done")
    ] = None,
) -> dict[str, Any]:
    """Update or close many openings in one asynchronous request. Write operation.

    Use to close all of a job's openings at once (list_job_openings → ids).
    Returns bulk_action_uuid; check progress with get_bulk_request_status.
    """
    data = []
    for item in openings:
        entry = dict(item)
        if "custom_fields" in entry:
            # v3 replaces each opening's whole collection: merge with current values.
            merged = await merged_custom_fields(
                client, "/openings", entry["id"], entry["custom_fields"]
            )
            if client._is_error(merged):
                return merged  # type: ignore[return-value]
            entry["custom_fields"] = merged
        data.append(entry)
    body: dict[str, Any] = {"data": data}
    if callback_url is not None:
        body["callback_url"] = callback_url
    return await client.harvest_patch("/openings/bulk", json_data=body)


async def bulk_delete_job_openings(
    client: GreenhouseClient,
    *,
    opening_ids: Annotated[
        list[int], Field(description="Greenhouse opening IDs to delete — from list_job_openings")
    ],
    callback_url: Annotated[
        str | None, Field(description="Optional HTTPS URL Greenhouse POSTs to when done")
    ] = None,
) -> dict[str, Any]:
    """Delete many openings in one asynchronous request. Destructive — cannot be undone.

    Returns bulk_action_uuid; check progress with get_bulk_request_status.
    """
    body: dict[str, Any] = {"data": list(opening_ids)}
    if callback_url is not None:
        body["callback_url"] = callback_url
    return await client.harvest_delete("/openings/bulk", json_data=body)


async def get_bulk_request_status(
    client: GreenhouseClient,
    *,
    bulk_action_uuid: Annotated[
        str, Field(description="bulk_action_uuid returned by any bulk tool")
    ],
) -> dict[str, Any]:
    """Check the progress of any v3 bulk request. Read-only.

    Use after a bulk tool returns a bulk_action_uuid (bulk job openings, custom field
    options in batches over 50). Returns status (building/pending/in_progress/completed/failed),
    record_count, success_count, failure_count, and short-lived result URLs.
    """
    result = await client.harvest_get(f"/bulk_requests/{bulk_action_uuid}")
    if client._is_error(result):
        return result
    items = result.get("items") or []
    if not items:
        return client._error_dict(404, {"message": f"No bulk request {bulk_action_uuid}"})
    return items[0]  # type: ignore[no-any-return]
