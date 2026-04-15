"""Harvest API — Prospect Pools tools (2 tools)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_prospect_pools(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    page: Annotated[int, Field(description="Page number (starts at 1)")] = 1,
    paginate: Annotated[str, Field(description="'single' for one page, 'all' to auto-fetch every page")] = "single",
) -> dict[str, Any]:
    """List all prospect pools with their stages. Read-only.

    Prospect pools organize sourced candidates before they enter job pipelines.
    Pool IDs are used in add_prospect (prospect_pool_id). To move a prospect into
    a job pipeline, use convert_prospect.
    """
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get("/prospect_pools", params=params, paginate=paginate)


async def get_prospect_pool(
    client: GreenhouseClient,
    *,
    prospect_pool_id: Annotated[int, Field(description="Prospect pool ID — get from list_prospect_pools")],
) -> dict[str, Any]:
    """Get a single prospect pool with its stages by ID. Read-only.

    Returns the pool name and available stages. Use list_prospect_pools to find
    pool IDs. Prospects are added to pools via add_prospect.
    """
    return await client.harvest_get_one(f"/prospect_pools/{prospect_pool_id}")
