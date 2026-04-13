"""Ingestion API — Post tracking link (1 tool)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def post_tracking_link(
    client: GreenhouseClient,
    *,
    job_id: int,
    source: str,
    referrer: str | None = None,
) -> dict[str, Any]:
    """Create a tracking link for a job."""
    data: dict[str, Any] = {"job_id": job_id, "source": source}
    if referrer:
        data["referrer"] = referrer
    return await client.ingestion_post("/tracking_links", json_data=data)
