"""Harvest API — Attachment reading tools (2 tools)."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


def _full_name(candidate: dict[str, Any]) -> str:
    return f"{candidate.get('first_name') or ''} {candidate.get('last_name') or ''}".strip()


async def read_candidate_resume(
    client: GreenhouseClient,
    *,
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
) -> dict[str, Any]:
    """Download and return a candidate's most recent resume text. Read-only.

    Users say "pull up Sarah's resume" or "show me John's CV." To find
    candidate_id: search_candidates_by_name. Returns extracted text from
    the most recently uploaded resume across all the candidate's applications.
    For batch reading, use batch_read_resumes.
    """
    candidate, attachments = await asyncio.gather(
        client.harvest_get_by_id("/candidates", candidate_id),
        client.harvest_get(
            "/attachments", params={"candidate_ids": [candidate_id]}, paginate="all"
        ),
    )
    if client._is_error(candidate):
        return candidate
    if client._is_error(attachments):
        return attachments

    items: list[dict[str, Any]] = attachments.get("items", [])
    resumes = [a for a in items if a.get("type") == "resume"]
    if not resumes:
        return {
            "error": "No resume found for this candidate.",
            "candidate_id": candidate_id,
            "candidate_name": _full_name(candidate),
            "attachment_count": len(items),
            "attachment_types": [a.get("type") for a in items],
        }

    resume = max(resumes, key=lambda a: a.get("created_at") or "")
    url = resume.get("url")
    if not url:
        return {"error": "Resume URL not available.", "candidate_id": candidate_id}

    content = await client.download_url(url)
    content["filename"] = resume.get("filename", "resume")
    content["application_id"] = resume.get("application_id")
    content["candidate_id"] = candidate_id
    content["candidate_name"] = _full_name(candidate)
    return content


async def download_attachment(
    client: GreenhouseClient,
    *,
    url: Annotated[
        str,
        Field(
            description="Attachment URL — from get_candidate's or get_application's "
            "attachments array"
        ),
    ],
) -> dict[str, Any]:
    """Download content from a Greenhouse attachment URL. Read-only.

    Use when you have a specific attachment URL from a candidate or application
    record (e.g., get_candidate's or get_application's attachments array).
    Attachment URLs are time-limited — if a download fails, fetch the record
    again for a fresh URL.
    """
    return await client.download_url(url)
