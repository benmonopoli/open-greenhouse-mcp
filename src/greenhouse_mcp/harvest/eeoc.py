"""Harvest API — EEOC tools (2 tools)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_eeoc(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    page: Annotated[int, Field(description="Page number (starts at 1)")] = 1,
    paginate: Annotated[str, Field(description="'single' for one page, 'all' to auto-fetch every page")] = "single",
) -> dict[str, Any]:
    """List all EEOC data collected from applications. Read-only.

    Compliance data — self-reported race, gender, veteran, and disability
    status. Used for federal reporting, not for hiring decisions.
    """
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get("/eeoc", params=params, paginate=paginate)


async def get_eeoc_for_application(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
) -> dict[str, Any]:
    """Get EEOC data for a specific application. Read-only.

    To find application_id: search_candidates_by_name → get_candidate →
    match the application to the job.
    """
    return await client.harvest_get_one(f"/applications/{application_id}/eeoc")
