"""Ingestion API — Post candidates (1 tool)."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def post_candidate(
    client: GreenhouseClient,
    *,
    first_name: Annotated[str, Field(description="Candidate's first name")],
    last_name: Annotated[str, Field(description="Candidate's last name")],
    email: Annotated[str, Field(description="Candidate's email address")],
    job_id: Annotated[int | None, Field(description="Job to apply to — retrieve_ingestion_jobs to find")] = None,
    phone: Annotated[str | None, Field(description="Candidate's phone number")] = None,
    resume: Annotated[str | None, Field(description="Resume content or URL")] = None,
    source: Annotated[str | None, Field(description="Source name (free text)")] = None,
    prospect: Annotated[bool, Field(description="True to create as prospect instead of applicant")] = False,
) -> dict[str, Any]:
    """Submit a candidate via the Ingestion API (partner integration). Write operation.

    For internal candidate creation (as recruiter/admin), use create_candidate
    and create_application instead. This is the partner/integration endpoint.
    """
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
