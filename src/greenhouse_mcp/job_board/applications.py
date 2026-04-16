"""Job Board API — Application submission (1 tool)."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def submit_application(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Board job ID — from list_board_jobs")],
    first_name: Annotated[str, Field(description="Applicant's first name")],
    last_name: Annotated[str, Field(description="Applicant's last name")],
    email: Annotated[str, Field(description="Applicant's email address")],
    phone: Annotated[str | None, Field(description="Applicant's phone number")] = None,
    resume: Annotated[str | None, Field(description="Resume content or URL")] = None,
    cover_letter: Annotated[str | None, Field(description="Cover letter text")] = None,
    mapped_url_token: Annotated[str | None, Field(description="Tracking link token for source attribution")] = None,
) -> dict[str, Any]:
    """Submit an application through the public job board. Write operation.

    For internal application creation (as a recruiter/admin), use
    create_application instead. This endpoint mirrors what external candidates
    do when they apply through the public board.
    """
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
