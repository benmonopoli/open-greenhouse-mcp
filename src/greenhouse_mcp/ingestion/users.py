"""Ingestion API — Retrieve current user (1 tool)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def retrieve_current_user(client: GreenhouseClient) -> dict[str, Any]:
    """Retrieve the current partner user via Ingestion API."""
    return await client.ingestion_get("/current_user")
