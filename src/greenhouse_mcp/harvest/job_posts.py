"""Harvest API — Job Posts tools (9 tools)."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient
from greenhouse_mcp.harvest.jobs import _by_id, _lookup, _with_warnings

_STATUS_MAP = {"live": "live", "offline": "draft", "draft": "draft"}


async def _attach_locations(
    client: GreenhouseClient, posts: list[dict[str, Any]], warnings: list[str]
) -> None:
    """Add ``locations`` (from /job_post_locations) to each post, in place.

    Office-type locations get the office name; custom-list ones the custom location value.
    """
    locs = await _lookup(
        client, "/job_post_locations", {p.get("id") for p in posts}, warnings,
        filter_name="job_post_ids",
    )
    office_ids = {loc.get("office_id") for loc in locs}
    custom_ids = {loc.get("custom_location_id") for loc in locs}
    offices = _by_id(await _lookup(client, "/offices", office_ids, warnings))
    customs = _by_id(await _lookup(client, "/job_board_custom_locations", custom_ids, warnings))
    by_post: dict[int, list[dict[str, Any]]] = {}
    for loc in locs:
        name = loc.get("plain_text_location")
        if loc.get("type") == "office":
            name = offices.get(loc.get("office_id") or 0, {}).get("name") or name
        elif loc.get("type") == "custom_list":
            name = customs.get(loc.get("custom_location_id") or 0, {}).get("value") or name
        by_post.setdefault(loc.get("job_post_id") or 0, []).append({**loc, "name": name})
    for post in posts:
        post["locations"] = by_post.get(post.get("id") or 0, [])


async def _list_posts(
    client: GreenhouseClient, params: dict[str, Any], paginate: str
) -> dict[str, Any]:
    result = await client.harvest_get("/job_posts", params=params, paginate=paginate)
    if client._is_error(result):
        return result
    warnings: list[str] = []
    await _attach_locations(client, result.get("items", []), warnings)
    return _with_warnings(result, warnings)


async def list_job_posts(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    cursor: Annotated[
        str | None,
        Field(description="Pass next_cursor from the previous response to get the next page"),
    ] = None,
    live: Annotated[
        bool | None,
        Field(
            description="Filter: true for published posts only, false for unpublished only, "
            "omit for all"
        ),
    ] = None,
    internal: Annotated[
        bool | None,
        Field(description="true for internal (employee) board posts, false for external only"),
    ] = None,
    paginate: Annotated[
        str, Field(description="'single' for one page, 'all' to auto-fetch every page")
    ] = "single",
) -> dict[str, Any]:
    """List all job posts (public listings) across all jobs. Read-only.

    A job post is the public-facing listing for a job. Each post includes its
    application form questions and a locations array (a post can have several
    locations in v3). For posts on a specific job, use list_job_posts_for_job
    (job_id from list_jobs → match by name).
    """
    params: dict[str, Any] = {
        "per_page": per_page,
        "cursor": cursor,
        "live": live,
        "internal": internal,
    }
    return await _list_posts(client, params, paginate)


async def list_job_posts_for_job(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
) -> dict[str, Any]:
    """List job posts for a specific job. Read-only.

    To find job_id: list_jobs → match by name. Returns the public listing(s)
    including title, content, live status, public_url, application questions,
    and locations.
    """
    return await _list_posts(client, {"job_ids": [job_id], "per_page": 500}, "all")


async def get_job_post(
    client: GreenhouseClient,
    *,
    job_post_id: Annotated[
        int, Field(description="Job post ID — get from list_job_posts or list_job_posts_for_job")
    ],
) -> dict[str, Any]:
    """Get a job post by ID. Read-only.

    Returns title, content (HTML), live status, job_id, job_board_id,
    public_url, application questions, and locations. To find post IDs:
    list_job_posts_for_job.
    """
    post = await client.harvest_get_by_id("/job_posts", job_post_id)
    if client._is_error(post):
        return post
    warnings: list[str] = []
    await _attach_locations(client, [post], warnings)
    return _with_warnings(post, warnings)


async def get_job_post_for_job(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    job_post_id: Annotated[int, Field(description="Job post ID")],
) -> dict[str, Any]:
    """Get a specific job post scoped to a job. Read-only.

    Same as get_job_post, but returns 404 if the post doesn't belong to the job.
    To find job_id: list_jobs → match by name. To find post_id:
    list_job_posts_for_job.
    """
    post = await get_job_post(client, job_post_id=job_post_id)
    if client._is_error(post):
        return post
    if post.get("job_id") != job_id:
        return client._error_dict(
            404, {"message": f"Job post {job_post_id} does not belong to job {job_id}"}
        )
    return post


async def get_job_post_custom_locations(
    client: GreenhouseClient,
    *,
    job_post_id: Annotated[int, Field(description="Job post ID — get from list_job_posts")],
) -> dict[str, Any]:
    """Get the custom-list locations selected on a job post. Read-only.

    Custom locations are per-job-board dropdown values. Returns
    {"items": [{id, value, active, greenhouse_job_board_id, job_post_location_id}]}.
    For all of a post's locations (free text, office, custom), use get_job_post.
    To find job_post_id: list_job_posts_for_job.
    """
    warnings: list[str] = []
    locs = await client.harvest_get(
        "/job_post_locations",
        params={"job_post_ids": [job_post_id], "type": "custom_list", "per_page": 500},
        paginate="all",
    )
    if client._is_error(locs):
        return locs
    loc_by_custom = {
        loc.get("custom_location_id"): loc.get("id") for loc in locs.get("items", [])
    }
    customs = await _lookup(client, "/job_board_custom_locations", set(loc_by_custom), warnings)
    items = [{**c, "job_post_location_id": loc_by_custom.get(c.get("id"))} for c in customs]
    return _with_warnings({"items": items, "total": len(items)}, warnings)


async def update_job_post(
    client: GreenhouseClient,
    *,
    job_post_id: Annotated[int, Field(description="Job post ID to update")],
    title: Annotated[str | None, Field(description="New post title")] = None,
    location: Annotated[
        str | None,
        Field(
            description="New free-text location. Replaces the post's existing locations; "
            "use add_job_post_location to add one instead"
        ),
    ] = None,
    content: Annotated[
        str | None, Field(description="New post body content (HTML supported)")
    ] = None,
) -> dict[str, Any]:
    """Update a job post's title, location, or content. Write operation — admin only.

    To find job_post_id: list_job_posts_for_job (job_id from list_jobs →
    match by name). In v3 locations are separate records: passing location
    adds it as a free-text location and then removes the post's previous
    locations. For multiple or office-based locations, use
    add_job_post_location / remove_job_post_location.
    """
    result: dict[str, Any] = {}
    json_data: dict[str, Any] = {}
    if title is not None:
        json_data["title"] = title
    if content is not None:
        json_data["content"] = content
    if json_data:
        result = await client.harvest_patch(f"/job_posts/{job_post_id}", json_data=json_data)
        if client._is_error(result):
            return result
    if location is not None:
        existing = await client.harvest_get(
            "/job_post_locations",
            params={"job_post_ids": [job_post_id], "per_page": 500},
            paginate="all",
        )
        if client._is_error(existing):
            return existing
        created = await client.harvest_post(
            "/job_post_locations",
            json_data={"job_post_id": job_post_id, "type": "free_text", "value": location},
        )
        if client._is_error(created):
            return created
        removed: list[int] = []
        failed: list[dict[str, Any]] = []
        for loc in existing.get("items", []):
            deleted = await client.harvest_delete(f"/job_post_locations/{loc['id']}")
            if client._is_error(deleted):
                failed.append({"id": loc["id"], "error": deleted})
            else:
                removed.append(loc["id"])
        result = result or {"id": job_post_id}
        result["location"] = created
        result["removed_location_ids"] = removed
        if failed:
            result["location_remove_errors"] = failed
    if not result:
        return {"error": "Provide at least one of title, location, or content.",
                "status_code": 422}
    return result


async def update_job_post_status(
    client: GreenhouseClient,
    *,
    job_post_id: Annotated[int, Field(description="Job post ID to update")],
    status: Annotated[
        str, Field(description="New status: 'live' (published) or 'offline' (unpublished draft)")
    ],
) -> dict[str, Any]:
    """Publish or unpublish a job post. Write operation.

    Controls visibility on job boards ('offline' sets the post back to draft).
    To find job_post_id: list_job_posts_for_job (job_id from list_jobs →
    match by name).
    """
    mapped = _STATUS_MAP.get(status.lower())
    if mapped is None:
        return {"error": "status must be 'live' or 'offline'", "status_code": 422}
    return await client.harvest_patch(
        f"/job_posts/{job_post_id}", json_data={"job_application_status": mapped}
    )


async def add_job_post_location(
    client: GreenhouseClient,
    *,
    job_post_id: Annotated[int, Field(description="Job post ID — get from list_job_posts")],
    value: Annotated[
        str,
        Field(
            description="Location value: the text (free_text), an office ID from list_offices "
            "(office), or a custom location ID from get_job_post_custom_locations (custom_list)"
        ),
    ],
    type: Annotated[
        str, Field(description="'free_text' (default), 'office', or 'custom_list'")
    ] = "free_text",
) -> dict[str, Any]:
    """Add a location to a job post. Write operation — admin only.

    v3 job posts can have several locations. The post's job board must allow
    the location type. To find job_post_id: list_job_posts_for_job.
    """
    return await client.harvest_post(
        "/job_post_locations",
        json_data={"job_post_id": job_post_id, "type": type, "value": str(value)},
    )


async def remove_job_post_location(
    client: GreenhouseClient,
    *,
    job_post_location_id: Annotated[
        int,
        Field(description="Job post location ID — the id in a post's locations array"),
    ],
) -> dict[str, Any]:
    """Remove a location from a job post. Write operation.

    To find job_post_location_id: get_job_post → locations[].id.
    """
    return await client.harvest_delete(f"/job_post_locations/{job_post_location_id}")
