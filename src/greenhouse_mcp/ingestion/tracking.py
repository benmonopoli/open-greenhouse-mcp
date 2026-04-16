"""Ingestion API — Post tracking link (1 tool)."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def post_tracking_link(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Job ID — retrieve_ingestion_jobs to find")],
    source: Annotated[str, Field(description="Source name for attribution")],
    referrer: Annotated[str | None, Field(description="Referrer name or identifier")] = None,
) -> dict[str, Any]:
    """Create a tracking link for source attribution on a job. Write operation.

    Generates a URL that attributes future applications to this source.
    """
    data: dict[str, Any] = {"job_id": job_id, "source": source}
    if referrer:
        data["referrer"] = referrer
    return await client.ingestion_post("/tracking_links", json_data=data)
