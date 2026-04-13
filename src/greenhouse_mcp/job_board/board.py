"""Job Board API — Board metadata (1 tool)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def get_board(client: GreenhouseClient) -> dict[str, Any]:
    """Get job board metadata (name, content, departments, offices)."""
    return await client.board_get("")
