"""Job Board API — Education reference data (3 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_board_degrees(client: GreenhouseClient) -> dict[str, Any]:
    """List degree types available on the job board."""
    return await client.board_get("/education/degrees")


async def list_board_disciplines(client: GreenhouseClient) -> dict[str, Any]:
    """List academic disciplines available on the job board."""
    return await client.board_get("/education/disciplines")


async def list_board_schools(client: GreenhouseClient) -> dict[str, Any]:
    """List schools available on the job board."""
    return await client.board_get("/education/schools")
