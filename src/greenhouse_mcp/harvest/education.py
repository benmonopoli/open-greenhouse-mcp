"""Harvest API — Education tools (3 tools).

Harvest v3 models schools, degrees and disciplines as options on the candidate
custom fields ``school_name``, ``degree`` and ``discipline``.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def _list_options(
    client: GreenhouseClient,
    field_key: str,
    per_page: int,
    cursor: str | None,
    paginate: str,
    force_refresh: bool,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "custom_field_key": field_key,
        "active": True,
        "per_page": per_page,
        "cursor": cursor,
    }
    return await client.harvest_get_cached(
        "/custom_field_options", params=params, paginate=paginate, force_refresh=force_refresh
    )


async def list_degrees(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    cursor: Annotated[
        str | None,
        Field(description="Pass next_cursor from the previous response to get the next page"),
    ] = None,
    paginate: Annotated[
        str, Field(description="'single' for one page, 'all' to auto-fetch every page")
    ] = "single",
    force_refresh: Annotated[bool, Field(description="Bypass cache and fetch fresh data")] = False,
) -> dict[str, Any]:
    """List degree types (Bachelor's, Master's, PhD, etc.). Read-only.

    Resolves degree names to IDs (degree_id) for add_education. Each item is a
    custom field option with id and name.
    """
    return await _list_options(client, "degree", per_page, cursor, paginate, force_refresh)


async def list_disciplines(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    cursor: Annotated[
        str | None,
        Field(description="Pass next_cursor from the previous response to get the next page"),
    ] = None,
    paginate: Annotated[
        str, Field(description="'single' for one page, 'all' to auto-fetch every page")
    ] = "single",
    force_refresh: Annotated[bool, Field(description="Bypass cache and fetch fresh data")] = False,
) -> dict[str, Any]:
    """List academic disciplines (Computer Science, Business, etc.). Read-only.

    Resolves discipline names to IDs (discipline_id) for add_education. Each
    item is a custom field option with id and name.
    """
    return await _list_options(client, "discipline", per_page, cursor, paginate, force_refresh)


async def list_schools(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    cursor: Annotated[
        str | None,
        Field(description="Pass next_cursor from the previous response to get the next page"),
    ] = None,
    paginate: Annotated[
        str,
        Field(
            description="'single' for one page, 'all' to auto-fetch every page (the school "
            "list is long — use 'all' to search it by name)"
        ),
    ] = "single",
    force_refresh: Annotated[bool, Field(description="Bypass cache and fetch fresh data")] = False,
) -> dict[str, Any]:
    """List schools for education records. Read-only.

    Resolves school names to IDs (school_id) for add_education. Each item is a
    custom field option with id and name.
    """
    return await _list_options(client, "school_name", per_page, cursor, paginate, force_refresh)
