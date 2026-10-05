"""Harvest API — Activity Feed tools (1 tool)."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient, add_date_filter


async def get_activity_feed(
    client: GreenhouseClient,
    *,
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
    created_after: Annotated[
        str | None, Field(description="ISO 8601 datetime — only entries created after this")
    ] = None,
) -> dict[str, Any]:
    """Get a candidate's activity timeline. Read-only.

    Users say "show me Sarah's history" or "what's happened with this candidate?"
    To find candidate_id: search_candidates_by_name. Returns three lists,
    newest first: `notes` (notes, interviews, follow-ups and other entries),
    `emails` (logged emails with subject, email_from/email_to/email_cc), and
    `activities` (system events such as stage changes). Every entry has
    `type`, `body`, `created_at`, `application_id`, `visibility` and `user`
    ({id, name}) when a person wrote it.
    """
    params: dict[str, Any] = {"candidate_ids": [candidate_id], "per_page": 500}
    add_date_filter(params, "created_at", gt=created_after)
    result = await client.harvest_get("/notes", params=params, paginate="all")
    if client._is_error(result):
        return result
    entries: list[dict[str, Any]] = result.get("items", [])

    user_ids = [e["user_id"] for e in entries if e.get("user_id")]
    names: dict[Any, Any] = {}
    if user_ids:
        users = await client.harvest_get_ids("/users", "ids", user_ids)
        if not client._is_error(users):
            names = {u.get("id"): u.get("name") for u in users.get("items", [])}
    for entry in entries:
        uid = entry.get("user_id")
        entry["user"] = {"id": uid, "name": names.get(uid)} if uid else None

    entries.sort(key=lambda e: e.get("created_at") or "", reverse=True)
    feed: dict[str, Any] = {"notes": [], "emails": [], "activities": []}
    for entry in entries:
        kind = entry.get("type")
        bucket = "emails" if kind == "EMAIL" else "activities" if kind == "ACTIVITY" else "notes"
        feed[bucket].append(entry)
    feed["total"] = len(entries)
    if result.get("partial"):
        feed["partial"] = True
        feed["error"] = result.get("error")
    return feed
