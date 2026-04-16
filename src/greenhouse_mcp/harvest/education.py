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
    """List degree types (Bachelor's, Master's, PhD, etc.). Read-only.

    Resolves degree names to IDs for add_education.
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
    """List academic disciplines (Computer Science, Business, etc.). Read-only.

    Resolves discipline names to IDs for add_education.
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
    """List schools for education records. Read-only.

    Resolves school names to IDs for add_education.
    """
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get_cached("/schools", params=params, force_refresh=force_refresh)
