"""Job Board API — Department tools (2 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_board_departments(client: GreenhouseClient) -> dict[str, Any]:
    """List departments on the job board."""
    return await client.board_get("/departments")


async def get_board_department(
    client: GreenhouseClient, *, department_id: int
) -> dict[str, Any]:
    """Get a single department from the job board."""
    return await client.board_get(f"/departments/{department_id}")
