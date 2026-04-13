"""Harvest API — Job Posts tools (7 tools)."""
from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_job_posts(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    live: bool | None = None,
    paginate: str = "single",
) -> dict[str, Any]:
    """List all job posts, optionally filtered to only live (published) posts."""
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    if live is not None:
        params["live"] = live
    return await client.harvest_get("/job_posts", params=params, paginate=paginate)


async def list_job_posts_for_job(
    client: GreenhouseClient,
    *,
    job_id: int,
) -> dict[str, Any]:
    """List all job posts associated with a specific job."""
    return await client.harvest_get(f"/jobs/{job_id}/job_posts")


async def get_job_post(
    client: GreenhouseClient,
    *,
    job_post_id: int,
) -> dict[str, Any]:
    """Get a single job post by ID."""
    return await client.harvest_get(f"/job_posts/{job_post_id}")


async def get_job_post_for_job(
    client: GreenhouseClient,
    *,
    job_id: int,
    job_post_id: int,
) -> dict[str, Any]:
    """Get a specific job post scoped to a particular job."""
    return await client.harvest_get(f"/jobs/{job_id}/job_posts/{job_post_id}")


async def get_job_post_custom_locations(
    client: GreenhouseClient,
    *,
    job_post_id: int,
) -> dict[str, Any]:
    """Get custom location data for a specific job post."""
    return await client.harvest_get(f"/job_posts/{job_post_id}/custom_locations")


async def update_job_post(
    client: GreenhouseClient,
    *,
    job_post_id: int,
    title: str | None = None,
    location: str | None = None,
    content: str | None = None,
) -> dict[str, Any]:
    """Update a job post's title, location, or content."""
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
    job_post_id: int,
    status: str,
) -> dict[str, Any]:
    """Update a job post's publish status (e.g. live or offline)."""
    return await client.harvest_patch(
        f"/job_posts/{job_post_id}", json_data={"status": status}
    )
