"""Ingestion API — Retrieve candidates (1 tool)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def retrieve_ingestion_candidates(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
) -> dict[str, Any]:
    """Retrieve candidates submitted via the Ingestion API."""
    return await client.ingestion_get(
        "/candidates", params={"per_page": per_page, "page": page}
    )
