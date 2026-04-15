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

    Returns offers globally. For offers on a specific application, use
    list_offers_for_application instead. For the most recent offer on an application,
    use get_current_offer. An application can have multiple offers (revised offers).
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

    An application can have multiple offers (if revised). Returns them in chronological
    order. For just the current/latest offer, use get_current_offer. For all offers
    globally, use list_offers.
    """
    return await client.harvest_get(f"/applications/{application_id}/offers")


async def get_offer(
    client: GreenhouseClient,
    *,
    offer_id: Annotated[int, Field(description="Offer ID — get from list_offers or list_offers_for_application")],
) -> dict[str, Any]:
    """Get a single offer by ID. Read-only. Returns the offer details including
    status, start date, and custom fields.

    Use list_offers_for_application to find offer IDs for a candidate. For the
    current offer on an application, use get_current_offer (no offer ID needed).
    """
    return await client.harvest_get_one(f"/offers/{offer_id}")


async def get_current_offer(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
) -> dict[str, Any]:
    """Get the current (most recent) offer for an application. Read-only.

    Returns the latest offer regardless of status. Use this when you need the active
    offer without knowing the offer ID. For the full offer history, use
    list_offers_for_application. To update the current offer, use update_current_offer.
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

    Only updates the most recent offer. To view the current offer first, use
    get_current_offer. To finalize hiring after offer acceptance, use hire_application.
    """
    json_data: dict[str, Any] = {}
    if starts_at is not None:
        json_data["starts_at"] = starts_at
    if custom_fields is not None:
        json_data["custom_fields"] = custom_fields
    return await client.harvest_patch(
        f"/applications/{application_id}/offers/current_offer", json_data=json_data
    )
