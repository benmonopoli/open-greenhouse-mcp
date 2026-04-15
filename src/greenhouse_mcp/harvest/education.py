"""Harvest API — Education tools (3 tools)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_degrees(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    page: Annotated[int, Field(description="Page number (starts at 1)")] = 1,
    force_refresh: Annotated[bool, Field(description="Bypass cache and fetch fresh data")] = False,
) -> dict[str, Any]:
    """List all degree types (e.g. Bachelor's, Master's, PhD). Read-only. Uses cached data.

    Degree IDs are used in add_education. Pass force_refresh=true after changes.
    For disciplines, use list_disciplines. For schools, use list_schools.
    """
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get_cached("/degrees", params=params, force_refresh=force_refresh)


async def list_disciplines(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    page: Annotated[int, Field(description="Page number (starts at 1)")] = 1,
    force_refresh: Annotated[bool, Field(description="Bypass cache and fetch fresh data")] = False,
) -> dict[str, Any]:
    """List all academic disciplines (e.g. Computer Science, Business). Read-only. Uses cached data.

    Discipline IDs are used in add_education. Pass force_refresh=true after changes.
    For degrees, use list_degrees. For schools, use list_schools.
    """
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get_cached(
        "/disciplines", params=params, force_refresh=force_refresh
    )


async def list_schools(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    page: Annotated[int, Field(description="Page number (starts at 1)")] = 1,
    force_refresh: Annotated[bool, Field(description="Bypass cache and fetch fresh data")] = False,
) -> dict[str, Any]:
    """List all schools available for education records. Read-only. Uses cached data.

    School IDs are used in add_education. Pass force_refresh=true after changes.
    For degrees, use list_degrees. For disciplines, use list_disciplines.
    """
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get_cached("/schools", params=params, force_refresh=force_refresh)
