"""Harvest API — Candidate search tools (2 tools)."""
from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def search_candidates_by_name(
    client: GreenhouseClient,
    *,
    name: str,
    per_page: int = 500,
    max_pages: int = 10,
) -> dict[str, Any]:
    """Search candidates by first or last name (case-insensitive substring match).

    Use this when a recruiter says "pull up John's application" or "find Sarah Chen."
    Fetches candidates in pages and filters client-side since the Greenhouse API
    doesn't support name search directly. Returns up to max_pages * per_page candidates
    scanned, with all matches returned.

    Example: search_candidates_by_name(name="Sarah") finds "Sarah Chen", "Sarah O'Brien", etc.
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
    email: str,
) -> dict[str, Any]:
    """Search for a candidate by exact email address.

    Use this when you have a candidate's email and need their full profile.
    Returns the candidate record directly from the Greenhouse API.
    """
    return await client.harvest_get(
        "/candidates",
        params={"email": email, "per_page": 1},
        paginate="single",
    )
