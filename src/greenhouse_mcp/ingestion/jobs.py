"""Ingestion API — Retrieve jobs (1 tool)."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def retrieve_ingestion_jobs(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    page: Annotated[int, Field(description="Page number")] = 1,
) -> dict[str, Any]:
    """List jobs visible to the integration partner. Read-only.

    Partner-scoped version of list_jobs. Returns only jobs the integration
    has been granted access to.
    """
    return await client.ingestion_get(
        "/jobs", params={"per_page": per_page, "page": page}
    )
