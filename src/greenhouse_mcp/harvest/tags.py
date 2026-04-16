"""Harvest API — Tags tools (6 tools)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_tags(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    page: Annotated[int, Field(description="Page number (starts at 1)")] = 1,
    force_refresh: Annotated[bool, Field(description="Bypass cache and fetch fresh data")] = False,
) -> dict[str, Any]:
    """List all candidate tags in the organization. Read-only.

    Resolves tag names to IDs. When a user says "tag Sarah as 'strong hire',"
    use this to find the tag_id, then add_tag_to_candidate.
    """
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get_cached(
        "/tags/candidate", params=params, force_refresh=force_refresh
    )


async def create_tag(
    client: GreenhouseClient,
    *,
    name: Annotated[str, Field(description="Tag name — must be unique across the organization")],
) -> dict[str, Any]:
    """Create a new candidate tag. Write operation.

    After creating, use add_tag_to_candidate to apply it. Note: bulk_tag
    creates tags on-the-fly, so pre-creation isn't needed for bulk ops.
    """
    json_data: dict[str, Any] = {"name": name}
    return await client.harvest_post("/tags/candidate", json_data=json_data)


async def delete_tag(
    client: GreenhouseClient,
    *,
    tag_id: Annotated[int, Field(description="Tag ID to delete — get from list_tags")],
) -> dict[str, Any]:
    """Delete a tag from the organization. Destructive — removes it from all candidates.

    To find tag_id: list_tags → match by name.
    """
    return await client.harvest_delete(f"/tags/candidate/{tag_id}")


async def list_tags_on_candidate(
    client: GreenhouseClient,
    *,
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
) -> dict[str, Any]:
    """List tags on a specific candidate. Read-only.

    To find candidate_id: search_candidates_by_name.
    """
    return await client.harvest_get(f"/candidates/{candidate_id}/tags")


async def add_tag_to_candidate(
    client: GreenhouseClient,
    *,
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
    tag_id: Annotated[int, Field(description="Tag ID to apply — get from list_tags or create_tag")],
) -> dict[str, Any]:
    """Apply a tag to a candidate. Write operation.

    Users say "tag Sarah as 'referred'" or "mark John as strong hire." For
    candidate_id: search_candidates_by_name. For tag_id: list_tags → match
    by name. For bulk tagging, use bulk_tag instead.
    """
    return await client.harvest_put(f"/candidates/{candidate_id}/tags/{tag_id}")


async def remove_tag_from_candidate(
    client: GreenhouseClient,
    *,
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
    tag_id: Annotated[int, Field(description="Tag ID to remove — get from list_tags_on_candidate")],
) -> dict[str, Any]:
    """Remove a tag from a candidate. Write operation.

    For candidate_id: search_candidates_by_name. For tag_id:
    list_tags_on_candidate → find the tag, or list_tags → match by name.
    """
    return await client.harvest_delete(f"/candidates/{candidate_id}/tags/{tag_id}")
