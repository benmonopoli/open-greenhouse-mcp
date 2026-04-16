"""Harvest API — Offers tools (5 tools)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_offers(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    page: Annotated[int, Field(description="Page number (starts at 1)")] = 1,
    created_after: Annotated[str | None, Field(description="ISO 8601 datetime — only offers created after this")] = None,
    created_before: Annotated[str | None, Field(description="ISO 8601 datetime — only offers created before this")] = None,
    paginate: Annotated[str, Field(description="'single' for one page, 'all' to auto-fetch every page")] = "single",
) -> dict[str, Any]:
    """List all offers across all applications. Read-only.

    For offers on a specific candidate's application, use list_offers_for_application
    (search_candidates_by_name → get_candidate → match application → use its ID).
    """
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    if created_after is not None:
        params["created_after"] = created_after
    if created_before is not None:
        params["created_before"] = created_before
    return await client.harvest_get("/offers", params=params, paginate=paginate)


async def list_offers_for_application(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
) -> dict[str, Any]:
    """List all offers made on a specific application. Read-only.

    To find application_id: search_candidates_by_name → get_candidate → match
    the application to the job. For the current offer only, use get_current_offer.
    """
    return await client.harvest_get(f"/applications/{application_id}/offers")


async def get_offer(
    client: GreenhouseClient,
    *,
    offer_id: Annotated[int, Field(description="Offer ID — get from list_offers or list_offers_for_application")],
) -> dict[str, Any]:
    """Get a single offer by ID. Read-only.

    Returns offer status, start date, and custom fields.
    """
    return await client.harvest_get_one(f"/offers/{offer_id}")


async def get_current_offer(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
) -> dict[str, Any]:
    """Get the most recent offer for an application. Read-only.

    To find application_id: search_candidates_by_name → get_candidate → match
    the application to the job.
    """
    return await client.harvest_get_one(f"/applications/{application_id}/offers/current_offer")


async def update_current_offer(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
    starts_at: Annotated[str | None, Field(description="New start date as 'YYYY-MM-DD'")] = None,
    custom_fields: Annotated[list[dict[str, Any]] | None, Field(description="Array of {id: field_id, value: ...} — get field IDs from list_custom_fields")] = None,
) -> dict[str, Any]:
    """Update the current offer on an application. Write operation.

    To find application_id: search_candidates_by_name → get_candidate → match
    the application to the job. For custom field IDs: list_custom_fields.
    """
    json_data: dict[str, Any] = {}
    if starts_at is not None:
        json_data["starts_at"] = starts_at
    if custom_fields is not None:
        json_data["custom_fields"] = custom_fields
    return await client.harvest_patch(
        f"/applications/{application_id}/offers/current_offer", json_data=json_data
    )
