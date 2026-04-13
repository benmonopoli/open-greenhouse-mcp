"""Ingestion API — Retrieve jobs (1 tool)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def retrieve_ingestion_jobs(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
) -> dict[str, Any]:
    """Retrieve jobs visible to the partner via Ingestion API."""
    return await client.ingestion_get(
        "/jobs", params={"per_page": per_page, "page": page}
    )
