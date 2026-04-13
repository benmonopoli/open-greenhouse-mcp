"""Harvest API — Attachment reading tools (2 tools)."""
from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def read_candidate_resume(
    client: GreenhouseClient,
    *,
    candidate_id: int,
) -> dict[str, Any]:
    """Download and return a candidate's most recent resume/CV content.

    Use this when screening a candidate — fetches the candidate record, finds
    the most recent resume attachment, and downloads it. Returns the file content
    (base64-encoded for binary files like PDFs, or plain text for text files)
    along with metadata.

    Example: "Screen John's resume for Python experience" — call this first to
    get the resume content, then analyze it.
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
    url: str,
) -> dict[str, Any]:
    """Download content from a Greenhouse attachment URL.

    Use this to fetch any attachment content — resumes, cover letters, work samples,
    or other files attached to candidate records. Pass the URL from a candidate's
    attachments list. Returns base64-encoded content for binary files or plain text.
    """
    return await client.download_url(url)
