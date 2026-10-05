"""Harvest API — EEOC tools (2 tools)."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient, add_date_filter


async def list_eeoc(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    cursor: Annotated[
        str | None,
        Field(description="Pass next_cursor from the previous response to get the next page"),
    ] = None,
    submitted_after: Annotated[
        str | None, Field(description="ISO 8601 datetime — only responses submitted after this")
    ] = None,
    submitted_before: Annotated[
        str | None, Field(description="ISO 8601 datetime — only responses submitted before this")
    ] = None,
    paginate: Annotated[
        str, Field(description="'single' for one page, 'all' to auto-fetch every page")
    ] = "single",
) -> dict[str, Any]:
    """List all EEOC data collected from applications. Read-only.

    Compliance data — self-reported race, gender, veteran, and disability
    status ({id, description} each). Used for federal reporting, not for
    hiring decisions.
    """
    params: dict[str, Any] = {"per_page": per_page}
    if cursor:
        params["cursor"] = cursor
    add_date_filter(params, "submitted_at", gt=submitted_after, lt=submitted_before)
    return await client.harvest_get("/eeoc", params=params, paginate=paginate)


async def get_eeoc_for_application(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
) -> dict[str, Any]:
    """Get EEOC data for a specific application. Read-only.

    To find application_id: search_candidates_by_name →
    list_applications(candidate_id=...) → match the application to the job.
    """
    result = await client.harvest_get("/eeoc", params={"application_ids": [application_id]})
    if client._is_error(result):
        return result
    items = result.get("items") or []
    if not items:
        return client._error_dict(
            404, {"message": f"No EEOC response for application {application_id}"}
        )
    return items[0]  # type: ignore[no-any-return]
