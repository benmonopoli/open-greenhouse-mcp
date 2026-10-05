"""Harvest API — Tags tools (6 tools).

Greenhouse v3 splits tags into the organization's tag dictionary
(``/candidate_tags``) and the tags applied to candidates (``/applied_candidate_tags``).
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_tags(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    cursor: Annotated[
        str | None,
        Field(description="Pass next_cursor from the previous response to get the next page"),
    ] = None,
    force_refresh: Annotated[bool, Field(description="Bypass cache and fetch fresh data")] = False,
) -> dict[str, Any]:
    """List all candidate tags in the organization. Read-only.

    Resolves tag names to IDs. When a user says "tag Sarah as 'strong hire',"
    use this to find the tag_id, then add_tag_to_candidate.
    """
    params: dict[str, Any] = {"per_page": per_page}
    if cursor:
        params["cursor"] = cursor
    return await client.harvest_get_cached(
        "/candidate_tags", params=params, force_refresh=force_refresh
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
    return await client.harvest_post("/candidate_tags", json_data=json_data)


async def delete_tag(
    client: GreenhouseClient,
    *,
    tag_id: Annotated[int, Field(description="Tag ID to delete — get from list_tags")],
) -> dict[str, Any]:
    """Delete a tag from the organization. Destructive — removes it from all candidates.

    To find tag_id: list_tags → match by name.
    """
    return await client.harvest_delete(f"/candidate_tags/{tag_id}")


async def list_tags_on_candidate(
    client: GreenhouseClient,
    *,
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
) -> dict[str, Any]:
    """List tags on a specific candidate. Read-only.

    To find candidate_id: search_candidates_by_name. Each item has the tag
    `id` and `name` (as in list_tags) plus `applied_tag_id`, the id of the
    tag-on-candidate record.
    """
    applied = await client.harvest_get(
        "/applied_candidate_tags",
        params={"candidate_ids": [candidate_id], "per_page": 500},
        paginate="all",
    )
    if client._is_error(applied):
        return applied
    rows = applied.get("items", [])
    names: dict[Any, Any] = {}
    tag_ids = [r["candidate_tag_id"] for r in rows if r.get("candidate_tag_id") is not None]
    if tag_ids:
        tags = await client.harvest_get_ids("/candidate_tags", "ids", tag_ids)
        if not client._is_error(tags):
            names = {t.get("id"): t.get("name") for t in tags.get("items", [])}
    items = [
        {
            "id": r.get("candidate_tag_id"),
            "name": names.get(r.get("candidate_tag_id")),
            "applied_tag_id": r.get("id"),
            "applied_at": r.get("created_at"),
        }
        for r in rows
    ]
    return {"items": items, "total": len(items)}


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
    json_data: dict[str, Any] = {"candidate_id": candidate_id, "candidate_tag_id": tag_id}
    return await client.harvest_post("/applied_candidate_tags", json_data=json_data)


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
    applied = await client.harvest_get(
        "/applied_candidate_tags",
        params={"candidate_ids": [candidate_id], "candidate_tag_ids": [tag_id]},
    )
    if client._is_error(applied):
        return applied
    rows = applied.get("items", [])
    if not rows:
        return {
            "error": f"Tag {tag_id} is not applied to candidate {candidate_id}.",
            "status_code": 404,
        }
    result: dict[str, Any] = {}
    for row in rows:
        result = await client.harvest_delete(f"/applied_candidate_tags/{row['id']}")
        if client._is_error(result):
            return result
    return result
