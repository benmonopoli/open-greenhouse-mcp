"""Job Board API — Department tools (2 tools)."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_board_departments(client: GreenhouseClient) -> dict[str, Any]:
    """List departments on the public job board. Read-only.

    For internal department management, use list_departments instead.
    """
    return await client.board_get("/departments")


async def get_board_department(
    client: GreenhouseClient,
    *,
    department_id: Annotated[int, Field(description="Board department ID — from list_board_departments")],
) -> dict[str, Any]:
    """Get a department from the public job board. Read-only."""
    return await client.board_get(f"/departments/{department_id}")
