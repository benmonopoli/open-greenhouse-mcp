"""Harvest API — Candidate search tools (2 tools)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def search_candidates_by_name(
    client: GreenhouseClient,
    *,
    name: Annotated[str, Field(description="Name to search — matches first or last name (case-insensitive substring)")],
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    max_pages: Annotated[int, Field(description="Maximum pages to fetch when auto-paginating")] = 10,
) -> dict[str, Any]:
    """Find candidates by name. Read-only — the starting point for most workflows.

    Users always refer to candidates by name, not ID. Use this first whenever
    a user mentions a candidate, then get_candidate on the match to see their
    full profile and application IDs. Case-insensitive substring match —
    "Sarah" finds "Sarah Chen", "Sarah O'Brien", etc.
    """
    name_lower = name.lower().strip()
    matches: list[dict[str, Any]] = []
    page = 1

    while page <= max_pages:
        result = await client.harvest_get(
            "/candidates",
            params={"per_page": per_page, "page": page},
            paginate="single",
        )
        if "error" in result and "status_code" in result:
            return result

        items = result.get("items", [])
        if not items:
            break

        for c in items:
            first = (c.get("first_name") or "").lower()
            last = (c.get("last_name") or "").lower()
            full = f"{first} {last}"
            if name_lower in first or name_lower in last or name_lower in full:
                matches.append(c)

        if not result.get("has_next"):
            break
        page += 1

    return {
        "matches": matches,
        "total_matches": len(matches),
        "pages_scanned": page,
    }


async def search_candidates_by_email(
    client: GreenhouseClient,
    *,
    email: Annotated[str, Field(description="Exact email address to search for")],
) -> dict[str, Any]:
    """Look up a candidate by exact email address. Read-only.

    Use when the user provides an email instead of a name. Returns the
    candidate record directly. For name-based lookup, use
    search_candidates_by_name.
    """
    return await client.harvest_get(
        "/candidates",
        params={"email": email, "per_page": 1},
        paginate="single",
    )
