"""Job Board API — Office tools (2 tools)."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_board_offices(client: GreenhouseClient) -> dict[str, Any]:
    """List offices on the public job board. Read-only.

    For internal office management, use list_offices instead.
    """
    return await client.board_get("/offices")


async def get_board_office(
    client: GreenhouseClient,
    *,
    office_id: Annotated[int, Field(description="Board office ID — from list_board_offices")],
) -> dict[str, Any]:
    """Get an office from the public job board. Read-only."""
    return await client.board_get(f"/offices/{office_id}")
