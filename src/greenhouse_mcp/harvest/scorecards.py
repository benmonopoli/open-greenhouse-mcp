"""Harvest API — Scorecards tools (3 tools)."""
from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_scorecards(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    created_after: str | None = None,
    created_before: str | None = None,
    paginate: str = "single",
) -> dict[str, Any]:
    """List all interview scorecards, with optional created date range filters."""
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    if created_after is not None:
        params["created_after"] = created_after
    if created_before is not None:
        params["created_before"] = created_before
    return await client.harvest_get("/scorecards", params=params, paginate=paginate)


async def list_scorecards_for_application(
    client: GreenhouseClient,
    *,
    application_id: int,
) -> dict[str, Any]:
    """List all scorecards submitted for a specific application."""
    return await client.harvest_get(f"/applications/{application_id}/scorecards")


async def get_scorecard(
    client: GreenhouseClient,
    *,
    scorecard_id: int,
) -> dict[str, Any]:
    """Get a single interview scorecard by ID."""
    return await client.harvest_get_one(f"/scorecards/{scorecard_id}")
