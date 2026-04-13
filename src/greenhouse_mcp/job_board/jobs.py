"""Job Board API — Published job tools (2 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_board_jobs(
    client: GreenhouseClient,
    *,
    content: bool = False,
) -> dict[str, Any]:
    """List all published jobs on the board."""
    params: dict[str, Any] = {}
    if content:
        params["content"] = "true"
    return await client.board_get("/jobs", params=params)


async def get_board_job(
    client: GreenhouseClient, *, job_id: int, questions: bool = False
) -> dict[str, Any]:
    """Get a published job with optional application questions."""
    params: dict[str, Any] = {}
    if questions:
        params["questions"] = "true"
    return await client.board_get(f"/jobs/{job_id}", params=params)
