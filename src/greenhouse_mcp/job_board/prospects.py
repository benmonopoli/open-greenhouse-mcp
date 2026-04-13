"""Job Board API — Prospect Post tools (2 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_prospect_post_sections(client: GreenhouseClient) -> dict[str, Any]:
    """List prospect post sections on the job board."""
    return await client.board_get("/prospect_posts")


async def get_prospect_post_section(
    client: GreenhouseClient, *, section_id: int
) -> dict[str, Any]:
    """Get a single prospect post section."""
    return await client.board_get(f"/prospect_posts/{section_id}")
