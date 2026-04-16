"""Ingestion API — Retrieve candidates (1 tool)."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def retrieve_ingestion_candidates(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    page: Annotated[int, Field(description="Page number")] = 1,
) -> dict[str, Any]:
    """List candidates submitted through the Ingestion API. Read-only.

    Shows candidates this integration has submitted. For the full candidate
    database, use list_candidates instead.
    """
    return await client.ingestion_get(
        "/candidates", params={"per_page": per_page, "page": page}
    )
