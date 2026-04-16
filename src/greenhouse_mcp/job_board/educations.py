"""Job Board API — Education reference data (3 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_board_degrees(client: GreenhouseClient) -> dict[str, Any]:
    """List degree types for board application forms. Read-only.

    Provides the degree dropdown options shown to external applicants.
    """
    return await client.board_get("/education/degrees")


async def list_board_disciplines(client: GreenhouseClient) -> dict[str, Any]:
    """List academic disciplines for board application forms. Read-only.

    Provides the discipline dropdown options shown to external applicants.
    """
    return await client.board_get("/education/disciplines")


async def list_board_schools(client: GreenhouseClient) -> dict[str, Any]:
    """List schools for board application forms. Read-only.

    Provides the school dropdown options shown to external applicants.
    """
    return await client.board_get("/education/schools")
