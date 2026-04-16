"""Harvest API — Attachment reading tools (2 tools)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def read_candidate_resume(
    client: GreenhouseClient,
    *,
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
) -> dict[str, Any]:
    """Download and return a candidate's most recent resume text. Read-only.

    Users say "pull up Sarah's resume" or "show me John's CV." To find
    candidate_id: search_candidates_by_name. Returns extracted text from
    the most recent resume attachment. For batch reading, use batch_read_resumes.
    """
    candidate = await client.harvest_get_one(f"/candidates/{candidate_id}")
    if "error" in candidate and "status_code" in candidate:
        return candidate

    attachments = candidate.get("attachments", [])
    resumes = [a for a in attachments if a.get("type") == "resume"]
    if not resumes:
        return {
            "error": "No resume found for this candidate.",
            "candidate_id": candidate_id,
            "candidate_name": f'{candidate.get("first_name", "")} '
            f'{candidate.get("last_name", "")}',
            "attachment_count": len(attachments),
            "attachment_types": [a.get("type") for a in attachments],
        }

    # Most recent resume (last in list)
    resume = resumes[-1]
    url = resume.get("url")
    if not url:
        return {"error": "Resume URL not available.", "candidate_id": candidate_id}

    content = await client.download_url(url)
    content["filename"] = resume.get("filename", "resume")
    content["candidate_id"] = candidate_id
    content["candidate_name"] = (
        f'{candidate.get("first_name", "")} {candidate.get("last_name", "")}'
    )
    return content


async def download_attachment(
    client: GreenhouseClient,
    *,
    url: Annotated[str, Field(description="Greenhouse attachment URL — get from candidate attachments or application data")],
) -> dict[str, Any]:
    """Download content from a Greenhouse attachment URL. Read-only.

    Use when you have a specific attachment URL from a candidate or application
    record (e.g., from get_candidate's attachments array).
    """
    return await client.download_url(url)
