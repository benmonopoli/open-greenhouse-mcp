"""Harvest API — Scorecards tools (3 tools)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_scorecards(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    page: Annotated[int, Field(description="Page number (starts at 1)")] = 1,
    created_after: Annotated[str | None, Field(description="ISO 8601 datetime — only scorecards created after this")] = None,
    created_before: Annotated[str | None, Field(description="ISO 8601 datetime — only scorecards created before this")] = None,
    paginate: Annotated[str, Field(description="'single' for one page, 'all' to auto-fetch every page")] = "single",
) -> dict[str, Any]:
    """List all interview scorecards across all applications. Read-only.

    Returns scorecards globally. For scorecards on a specific application, use
    list_scorecards_for_application instead. Scorecards are submitted by interviewers
    after interviews. For finding candidates missing scorecards, use
    candidates_needing_action.
    """
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    if created_after is not None:
        params["created_after"] = created_after
    if created_before is not None:
        params["created_before"] = created_before
    return await client.harvest_get("/scorecards", params=params, paginate=paginate)


async def list_scorecards_for_application(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
) -> dict[str, Any]:
    """List all scorecards submitted for a specific application. Read-only.

    Returns scorecards from all interview stages. For all scorecards globally, use
    list_scorecards. For scheduled interviews (not yet completed), use
    list_interviews_for_application.
    """
    return await client.harvest_get(f"/applications/{application_id}/scorecards")


async def get_scorecard(
    client: GreenhouseClient,
    *,
    scorecard_id: Annotated[int, Field(description="Scorecard ID — get from list_scorecards or list_scorecards_for_application")],
) -> dict[str, Any]:
    """Get a single interview scorecard by ID. Read-only. Returns the interviewer's
    ratings, attributes, and overall recommendation.

    Use list_scorecards_for_application to find scorecard IDs for a candidate.
    """
    return await client.harvest_get_one(f"/scorecards/{scorecard_id}")
