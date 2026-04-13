"""Harvest API — Offers tools (5 tools)."""
from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_offers(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    created_after: str | None = None,
    created_before: str | None = None,
    paginate: str = "single",
) -> dict[str, Any]:
    """List all offers, with optional created date range filters."""
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    if created_after is not None:
        params["created_after"] = created_after
    if created_before is not None:
        params["created_before"] = created_before
    return await client.harvest_get("/offers", params=params, paginate=paginate)


async def list_offers_for_application(
    client: GreenhouseClient,
    *,
    application_id: int,
) -> dict[str, Any]:
    """List all offers made on a specific application."""
    return await client.harvest_get(f"/applications/{application_id}/offers")


async def get_offer(
    client: GreenhouseClient,
    *,
    offer_id: int,
) -> dict[str, Any]:
    """Get a single offer by ID."""
    return await client.harvest_get_one(f"/offers/{offer_id}")


async def get_current_offer(
    client: GreenhouseClient,
    *,
    application_id: int,
) -> dict[str, Any]:
    """Get the current (most recent) offer for an application."""
    return await client.harvest_get_one(f"/applications/{application_id}/offers/current_offer")


async def update_current_offer(
    client: GreenhouseClient,
    *,
    application_id: int,
    starts_at: str | None = None,
    custom_fields: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Update the current offer on an application with a new start date or custom fields."""
    json_data: dict[str, Any] = {}
    if starts_at is not None:
        json_data["starts_at"] = starts_at
    if custom_fields is not None:
        json_data["custom_fields"] = custom_fields
    return await client.harvest_patch(
        f"/applications/{application_id}/offers/current_offer", json_data=json_data
    )
