"""Job Board API — Office tools (2 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_board_offices(client: GreenhouseClient) -> dict[str, Any]:
    """List offices on the job board."""
    return await client.board_get("/offices")


async def get_board_office(
    client: GreenhouseClient, *, office_id: int
) -> dict[str, Any]:
    """Get a single office from the job board."""
    return await client.board_get(f"/offices/{office_id}")
