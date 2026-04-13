"""Job Board API — Application submission (1 tool)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def submit_application(
    client: GreenhouseClient,
    *,
    job_id: int,
    first_name: str,
    last_name: str,
    email: str,
    phone: str | None = None,
    resume: str | None = None,
    cover_letter: str | None = None,
    mapped_url_token: str | None = None,
) -> dict[str, Any]:
    """Submit an application through the job board. Requires API key for auth."""
    data: dict[str, Any] = {
        "job_id": job_id,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
    }
    if phone:
        data["phone"] = phone
    if resume:
        data["resume"] = resume
    if cover_letter:
        data["cover_letter"] = cover_letter
    if mapped_url_token:
        data["mapped_url_token"] = mapped_url_token
    return await client.board_post("/applications", json_data=data)
