"""Job Board API — Published job tools (2 tools)."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_board_jobs(
    client: GreenhouseClient,
    *,
    content: Annotated[bool, Field(description="Include full job content/description")] = False,
) -> dict[str, Any]:
    """List all published jobs on the public job board. Read-only.

    Returns jobs visible to external candidates. For internal job data
    with pipeline info, use list_jobs instead.
    """
    params: dict[str, Any] = {}
    if content:
        params["content"] = "true"
    return await client.board_get("/jobs", params=params)


async def get_board_job(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Board job ID — from list_board_jobs")],
    questions: Annotated[bool, Field(description="Include application questions")] = False,
) -> dict[str, Any]:
    """Get a published job with optional application questions. Read-only.

    For internal job details (hiring team, custom fields), use get_job instead.
    """
    params: dict[str, Any] = {}
    if questions:
        params["questions"] = "true"
    return await client.board_get(f"/jobs/{job_id}", params=params)
