"""Harvest API — Prospect Pools tools (2 tools)."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def _attach_stages(
    client: GreenhouseClient, pools: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Nest each pool's stages (ordered by sort_order) as ``prospect_stages``."""
    pool_ids = [p["id"] for p in pools if p.get("id") is not None]
    if not pool_ids:
        return None
    stages = await client.harvest_get_ids("/prospect_pool_stages", "prospect_pool_ids", pool_ids)
    if client._is_error(stages):
        return stages
    by_pool: dict[Any, list[dict[str, Any]]] = {}
    for s in sorted(stages.get("items", []), key=lambda r: r.get("sort_order") or 0):
        by_pool.setdefault(s.get("prospect_pool_id"), []).append(s)
    for p in pools:
        p["prospect_stages"] = by_pool.get(p.get("id"), [])
    return None


async def list_prospect_pools(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    cursor: Annotated[
        str | None,
        Field(description="Pass next_cursor from the previous response to get the next page"),
    ] = None,
    active: Annotated[
        bool | None, Field(description="true = active pools only, false = inactive only")
    ] = None,
    paginate: Annotated[
        str, Field(description="'single' for one page, 'all' to auto-fetch every page")
    ] = "single",
) -> dict[str, Any]:
    """List all prospect pools with their stages. Read-only.

    Resolves pool names to IDs for add_prospect. Returns each pool's
    `prospect_stages` (ordered) for specifying a starting stage when adding
    prospects.
    """
    params: dict[str, Any] = {"per_page": per_page}
    if cursor:
        params["cursor"] = cursor
    if active is not None:
        params["active"] = active
    result = await client.harvest_get("/prospect_pools", params=params, paginate=paginate)
    if client._is_error(result):
        return result
    err = await _attach_stages(client, result.get("items", []))
    return err if err is not None else result


async def get_prospect_pool(
    client: GreenhouseClient,
    *,
    prospect_pool_id: Annotated[
        int, Field(description="Prospect pool ID — get from list_prospect_pools")
    ],
) -> dict[str, Any]:
    """Get a prospect pool and its stages by ID. Read-only.

    To find prospect_pool_id: list_prospect_pools → match by name.
    """
    pool = await client.harvest_get_by_id("/prospect_pools", prospect_pool_id)
    if client._is_error(pool):
        return pool
    err = await _attach_stages(client, [pool])
    return err if err is not None else pool
