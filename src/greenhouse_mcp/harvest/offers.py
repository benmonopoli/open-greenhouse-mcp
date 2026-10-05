"""Harvest API — Offers tools (5 tools).

v3 keeps every offer revision as its own row (``version``); the "current offer" is the
latest version on an application (``current_only=true``). ``starts_at``/``sent_at`` are
now ``starts_on``/``sent_on``.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient, add_date_filter
from greenhouse_mcp.harvest.jobs import _v3_custom_fields


async def list_offers(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    cursor: Annotated[
        str | None,
        Field(description="Pass next_cursor from the previous response to get the next page"),
    ] = None,
    created_after: Annotated[
        str | None, Field(description="ISO 8601 datetime — only offers created at/after this")
    ] = None,
    created_before: Annotated[
        str | None, Field(description="ISO 8601 datetime — only offers created before this")
    ] = None,
    status: Annotated[
        str | None,
        Field(description="Filter by status: 'Created', 'Accepted', 'Rejected', or 'Deprecated'"),
    ] = None,
    job_id: Annotated[
        int | None, Field(description="Only offers on this job — get ID from list_jobs")
    ] = None,
    current_only: Annotated[
        bool,
        Field(description="true to return only the latest version of each application's offer"),
    ] = False,
    paginate: Annotated[
        str, Field(description="'single' for one page, 'all' to auto-fetch every page")
    ] = "single",
) -> dict[str, Any]:
    """List offers across all applications. Read-only.

    Each offer has id, version, application_id, candidate_id, job_id,
    opening_id, status, starts_on, sent_on, resolved_at, and custom_fields.
    Every revision is returned (older ones have status 'Deprecated'); set
    current_only=true for just each application's current offer. For a specific
    candidate's offers, use list_offers_for_application
    (search_candidates_by_name → list_applications(candidate_id=...) → match
    the application → use its ID).
    """
    params: dict[str, Any] = {
        "per_page": per_page,
        "cursor": cursor,
        "status": status,
        "job_ids": [job_id] if job_id is not None else None,
        "current_only": current_only or None,
    }
    add_date_filter(params, "created_at", gte=created_after, lt=created_before)
    return await client.harvest_get("/offers", params=params, paginate=paginate)


async def list_offers_for_application(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
) -> dict[str, Any]:
    """List all offers (every version) made on a specific application. Read-only.

    Sorted newest version first. To find application_id:
    search_candidates_by_name → list_applications(candidate_id=...) → match
    the application to the job. For the current offer only, use get_current_offer.
    """
    result = await client.harvest_get(
        "/offers", params={"application_ids": [application_id], "per_page": 500}, paginate="all"
    )
    if client._is_error(result):
        return result
    result["items"] = sorted(
        result.get("items", []), key=lambda o: o.get("version") or 0, reverse=True
    )
    return result


async def get_offer(
    client: GreenhouseClient,
    *,
    offer_id: Annotated[
        int, Field(description="Offer ID — get from list_offers or list_offers_for_application")
    ],
) -> dict[str, Any]:
    """Get a single offer by ID. Read-only.

    Returns offer status, version, starts_on, sent_on, resolved_at, opening_id,
    and custom fields.
    """
    return await client.harvest_get_by_id("/offers", offer_id)


async def get_current_offer(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
) -> dict[str, Any]:
    """Get the current (latest version) offer for an application. Read-only.

    Returns 404 if the application has no offer. To find application_id:
    search_candidates_by_name → list_applications(candidate_id=...) → match
    the application to the job.
    """
    result = await client.harvest_get(
        "/offers",
        params={"application_ids": [application_id], "current_only": True, "per_page": 500},
        paginate="all",
    )
    if client._is_error(result):
        return result
    items = result.get("items") or []
    if not items:
        return client._error_dict(
            404, {"message": f"No offer found for application {application_id}"}
        )
    return max(items, key=lambda o: o.get("version") or 0)


async def update_current_offer(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
    starts_at: Annotated[str | None, Field(description="New start date as 'YYYY-MM-DD'")] = None,
    sent_on: Annotated[
        str | None, Field(description="Date the offer was sent, as 'YYYY-MM-DD'")
    ] = None,
    custom_fields: Annotated[
        list[dict[str, Any]] | None,
        Field(
            description="Array of {id, value} (or {custom_field_id, value}) — get field IDs "
            "from list_custom_fields"
        ),
    ] = None,
) -> dict[str, Any]:
    """Update the current offer on an application. Write operation.

    Looks up the application's latest offer version and patches it (start
    date → starts_on). To find application_id: search_candidates_by_name →
    list_applications(candidate_id=...) → match the application to the job.
    For custom field IDs: list_custom_fields.
    """
    offer = await get_current_offer(client, application_id=application_id)
    if client._is_error(offer):
        return offer
    json_data: dict[str, Any] = {}
    if starts_at is not None:
        json_data["starts_on"] = starts_at
    if sent_on is not None:
        json_data["sent_on"] = sent_on
    if custom_fields is not None:
        json_data["custom_fields"] = _v3_custom_fields(custom_fields)
    return await client.harvest_patch(f"/offers/{offer['id']}", json_data=json_data)
