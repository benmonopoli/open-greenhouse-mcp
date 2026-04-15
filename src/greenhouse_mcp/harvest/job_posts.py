"""Harvest API — Job Posts tools (7 tools)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_job_posts(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    page: Annotated[int, Field(description="Page number (starts at 1)")] = 1,
    live: Annotated[bool | None, Field(description="Filter: true for published posts only, false for drafts only, omit for all")] = None,
    paginate: Annotated[str, Field(description="'single' for one page, 'all' to auto-fetch every page")] = "single",
) -> dict[str, Any]:
    """List all job posts across all jobs. Read-only. A job post is the public-facing
    listing (title, description, location) for a job.

    Filter with live=true to see only published posts. For posts on a specific job,
    use list_job_posts_for_job. A single job can have multiple posts (e.g. different
    locations). For the job record itself (not the post), use get_job.
    """
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    if live is not None:
        params["live"] = live
    return await client.harvest_get("/job_posts", params=params, paginate=paginate)


async def list_job_posts_for_job(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
) -> dict[str, Any]:
    """List all job posts associated with a specific job. Read-only.

    A job can have multiple posts (e.g. different locations or boards). For all posts
    across all jobs, use list_job_posts. To get the job record itself, use get_job.
    """
    return await client.harvest_get(f"/jobs/{job_id}/job_posts")


async def get_job_post(
    client: GreenhouseClient,
    *,
    job_post_id: Annotated[int, Field(description="Job post ID — get from list_job_posts or list_job_posts_for_job")],
) -> dict[str, Any]:
    """Get a single job post by ID. Read-only. Returns the post title, location,
    content (HTML), status, and associated job.

    For custom location data on this post, use get_job_post_custom_locations. To
    find post IDs, use list_job_posts or list_job_posts_for_job.
    """
    return await client.harvest_get_one(f"/job_posts/{job_post_id}")


async def get_job_post_for_job(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    job_post_id: Annotated[int, Field(description="Job post ID")],
) -> dict[str, Any]:
    """Get a specific job post scoped to a particular job. Read-only.

    Similar to get_job_post but requires the job_id for authorization scoping. Use
    get_job_post if you only have the post ID. To list all posts for a job, use
    list_job_posts_for_job.
    """
    return await client.harvest_get_one(f"/jobs/{job_id}/job_posts/{job_post_id}")


async def get_job_post_custom_locations(
    client: GreenhouseClient,
    *,
    job_post_id: Annotated[int, Field(description="Job post ID — get from list_job_posts")],
) -> dict[str, Any]:
    """Get custom location data for a specific job post. Read-only.

    Returns additional location fields beyond the standard location string. Use
    get_job_post first to see the post's basic location, then this for extended
    location details if configured.
    """
    return await client.harvest_get_one(f"/job_posts/{job_post_id}/custom_locations")


async def update_job_post(
    client: GreenhouseClient,
    *,
    job_post_id: Annotated[int, Field(description="Job post ID to update")],
    title: Annotated[str | None, Field(description="New post title")] = None,
    location: Annotated[str | None, Field(description="New location string")] = None,
    content: Annotated[str | None, Field(description="New post body content (HTML supported)")] = None,
) -> dict[str, Any]:
    """Update a job post's title, location, or content. Write operation — admin only.

    Only updates fields you provide. This changes the public-facing listing. To change
    the post's publish status (live/offline), use update_job_post_status instead. To
    modify the job record itself, use update_job.
    """
    json_data: dict[str, Any] = {}
    if title is not None:
        json_data["title"] = title
    if location is not None:
        json_data["location"] = location
    if content is not None:
        json_data["content"] = content
    return await client.harvest_patch(f"/job_posts/{job_post_id}", json_data=json_data)


async def update_job_post_status(
    client: GreenhouseClient,
    *,
    job_post_id: Annotated[int, Field(description="Job post ID to update")],
    status: Annotated[str, Field(description="New status: 'live' (published) or 'offline' (hidden)")],
) -> dict[str, Any]:
    """Update a job post's publish status. Write operation — controls whether the
    post is visible on job boards.

    Set to 'live' to publish or 'offline' to hide. To modify post content instead
    (title, location, body), use update_job_post.
    """
    return await client.harvest_patch(
        f"/job_posts/{job_post_id}", json_data={"status": status}
    )
