"""Harvest API — Candidate search tools (2 tools)."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def search_candidates_by_name(
    client: GreenhouseClient,
    *,
    name: Annotated[
        str,
        Field(
            description="Name to search — matches first, last or preferred name "
            "(case-insensitive substring)"
        ),
    ],
    per_page: Annotated[int, Field(description="Candidates scanned per page (max 500)")] = 500,
    max_pages: Annotated[
        int, Field(description="Maximum pages to scan before stopping")
    ] = 10,
    cursor: Annotated[
        str | None,
        Field(
            description="Resume a scan: pass next_cursor from a previous response that had "
            "has_more=true"
        ),
    ] = None,
) -> dict[str, Any]:
    """Find candidates by name. Read-only — the starting point for most workflows.

    Users always refer to candidates by name, not ID. Use this first whenever
    a user mentions a candidate, then list_applications(candidate_id=...) to
    find their application IDs (candidate records don't include applications).
    Case-insensitive substring match — "Sarah" finds "Sarah Chen",
    "Sarah O'Brien", etc. Greenhouse has no name filter, so this scans up to
    max_pages × per_page candidates; if has_more is true, pass next_cursor to
    keep scanning.
    """
    name_lower = name.lower().strip()
    matches: list[dict[str, Any]] = []
    pages = 0
    next_cursor = cursor
    has_more = False

    while pages < max_pages:
        params: dict[str, Any] = (
            {"cursor": next_cursor} if next_cursor else {"per_page": min(per_page, 500)}
        )
        result = await client.harvest_get("/candidates", params=params, paginate="single")
        if client._is_error(result):
            if matches:
                break  # return what we found so far
            return result
        pages += 1

        for c in result.get("items", []):
            first = (c.get("first_name") or "").lower()
            last = (c.get("last_name") or "").lower()
            preferred = (c.get("preferred_name") or "").lower()
            full = f"{first} {last}"
            pref_full = f"{preferred} {last}"
            if any(name_lower in field for field in (first, last, full, preferred, pref_full)):
                matches.append(c)

        has_more = bool(result.get("has_next"))
        next_cursor = result.get("next_cursor")
        if not has_more or not next_cursor:
            has_more = False
            next_cursor = None
            break

    return {
        "matches": matches,
        "total_matches": len(matches),
        "pages_scanned": pages,
        "has_more": has_more,
        "next_cursor": next_cursor if has_more else None,
    }


async def search_candidates_by_email(
    client: GreenhouseClient,
    *,
    email: Annotated[str, Field(description="Exact email address to search for")],
) -> dict[str, Any]:
    """Look up a candidate by exact email address. Read-only.

    Use when the user provides an email instead of a name. Matches any email
    on the candidate's profile and returns the candidate record. For their
    applications, follow up with list_applications(candidate_id=...). For
    name-based lookup, use search_candidates_by_name.
    """
    return await client.harvest_get(
        "/candidates",
        params={"email": email, "per_page": 5},
        paginate="single",
    )
