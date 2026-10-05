"""Harvest API — Tracking Links tools (1 tool)."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def get_tracking_link(
    client: GreenhouseClient,
    *,
    token: Annotated[str, Field(description="Tracking link token string")],
) -> dict[str, Any]:
    """Get a tracking link by its token. Read-only.

    Returns the link's source_id, referrer_id, job_id, job_board_id and
    job_post_id, plus `source` ({id, name, type}) resolved from the source.
    The token is the gh_src value from the tracking URL.
    """
    result = await client.harvest_get("/tracking_links", params={"token": token})
    if client._is_error(result):
        return result
    items = result.get("items") or []
    if not items:
        return client._error_dict(404, {"message": f"No tracking link with token {token}"})
    link: dict[str, Any] = items[0]
    source_id = link.get("source_id")
    if source_id:
        sources = await client.harvest_get_cached(
            "/sources", params={"per_page": 500}, paginate="all"
        )
        if not client._is_error(sources):
            link["source"] = next(
                (s for s in sources.get("items", []) if s.get("id") == source_id), None
            )
    return link
