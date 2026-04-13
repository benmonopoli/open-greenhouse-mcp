"""Harvest API — Tags tools (6 tools)."""
from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_tags(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """List all candidate tags in the organization."""
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get_cached(
        "/tags/candidate", params=params, force_refresh=force_refresh
    )


async def create_tag(
    client: GreenhouseClient,
    *,
    name: str,
) -> dict[str, Any]:
    """Create a new candidate tag with the given name."""
    json_data: dict[str, Any] = {"name": name}
    return await client.harvest_post("/tags/candidate", json_data=json_data)


async def delete_tag(
    client: GreenhouseClient,
    *,
    tag_id: int,
) -> dict[str, Any]:
    """Delete a candidate tag by ID."""
    return await client.harvest_delete(f"/tags/candidate/{tag_id}")


async def list_tags_on_candidate(
    client: GreenhouseClient,
    *,
    candidate_id: int,
) -> dict[str, Any]:
    """List all tags applied to a specific candidate."""
    return await client.harvest_get(f"/candidates/{candidate_id}/tags")


async def add_tag_to_candidate(
    client: GreenhouseClient,
    *,
    candidate_id: int,
    tag_id: int,
) -> dict[str, Any]:
    """Apply a tag to a candidate."""
    return await client.harvest_put(f"/candidates/{candidate_id}/tags/{tag_id}")


async def remove_tag_from_candidate(
    client: GreenhouseClient,
    *,
    candidate_id: int,
    tag_id: int,
) -> dict[str, Any]:
    """Remove a tag from a candidate."""
    return await client.harvest_delete(f"/candidates/{candidate_id}/tags/{tag_id}")
