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
    """List all candidate tags in the organization. Read-only. Uses cached data by default.

    Tags are labels applied to candidates for categorization. Use the returned tag
    IDs with add_tag_to_candidate or bulk_tag. To see tags on a specific candidate,
    use list_tags_on_candidate. To create a new tag, use create_tag.
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

    Tags are organization-wide labels applied to candidates. After creation, apply
    to candidates with add_tag_to_candidate or bulk_tag. To delete, use delete_tag.
    Note: create_candidate also accepts tag names directly and creates tags on-the-fly.
    """
    json_data: dict[str, Any] = {"name": name}
    return await client.harvest_post("/tags/candidate", json_data=json_data)


async def delete_tag(
    client: GreenhouseClient,
    *,
    tag_id: Annotated[int, Field(description="Tag ID to delete — get from list_tags")],
) -> dict[str, Any]:
    """Delete a candidate tag. Destructive — removes the tag from all candidates.

    The tag is removed globally. To remove a tag from a single candidate without
    deleting it, use remove_tag_from_candidate instead.
    """
    return await client.harvest_delete(f"/tags/candidate/{tag_id}")


async def list_tags_on_candidate(
    client: GreenhouseClient,
    *,
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
) -> dict[str, Any]:
    """List all tags applied to a specific candidate. Read-only.

    To add a tag, use add_tag_to_candidate. To remove, use remove_tag_from_candidate.
    For all available tags in the organization, use list_tags.
    """
    return await client.harvest_get(f"/candidates/{candidate_id}/tags")


async def add_tag_to_candidate(
    client: GreenhouseClient,
    *,
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
    tag_id: Annotated[int, Field(description="Tag ID to apply — get from list_tags or create_tag")],
) -> dict[str, Any]:
    """Apply a tag to a candidate. Write operation.

    Tags are additive — this won't remove existing tags. For tagging multiple
    candidates at once, use bulk_tag. To remove a tag, use remove_tag_from_candidate.
    To see current tags, use list_tags_on_candidate.
    """
    return await client.harvest_put(f"/candidates/{candidate_id}/tags/{tag_id}")


async def remove_tag_from_candidate(
    client: GreenhouseClient,
    *,
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
    tag_id: Annotated[int, Field(description="Tag ID to remove — get from list_tags_on_candidate")],
) -> dict[str, Any]:
    """Remove a tag from a candidate. Write operation.

    Only removes the tag from this candidate — the tag still exists for other
    candidates. To delete the tag entirely, use delete_tag. To add tags, use
    add_tag_to_candidate.
    """
    return await client.harvest_delete(f"/candidates/{candidate_id}/tags/{tag_id}")
