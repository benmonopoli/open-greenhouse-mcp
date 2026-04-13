"""Ingestion API — Post candidates (1 tool)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def post_candidate(
    client: GreenhouseClient,
    *,
    first_name: str,
    last_name: str,
    email: str,
    job_id: int | None = None,
    phone: str | None = None,
    resume: str | None = None,
    source: str | None = None,
    prospect: bool = False,
) -> dict[str, Any]:
    """Submit a candidate or prospect via the Ingestion API."""
    data: dict[str, Any] = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "prospect": prospect,
    }
    if job_id:
        data["job_id"] = job_id
    if phone:
        data["phone"] = phone
    if resume:
        data["resume"] = resume
    if source:
        data["source"] = source
    return await client.ingestion_post("/candidates", json_data=data)
