"""Ingestion API — Retrieve prospect pools (1 tool)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def retrieve_prospect_pools(
    client: GreenhouseClient,
) -> dict[str, Any]:
    """List prospect pools via the Ingestion API. Read-only.

    Partner-scoped version of list_prospect_pools.
    """
    return await client.ingestion_get("/prospect_pools")
