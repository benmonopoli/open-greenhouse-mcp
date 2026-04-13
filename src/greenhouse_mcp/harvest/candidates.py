"""Harvest API — Candidates tools (15 tools)."""
from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_candidates(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    email: str | None = None,
    candidate_ids: list[int] | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
    updated_after: str | None = None,
    updated_before: str | None = None,
    paginate: str = "single",
) -> dict[str, Any]:
    """List all candidates with optional filters for email, IDs, and date ranges."""
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    if email is not None:
        params["email"] = email
    if candidate_ids is not None:
        params["candidate_ids"] = ",".join(str(i) for i in candidate_ids)
    if created_after is not None:
        params["created_after"] = created_after
    if created_before is not None:
        params["created_before"] = created_before
    if updated_after is not None:
        params["updated_after"] = updated_after
    if updated_before is not None:
        params["updated_before"] = updated_before
    return await client.harvest_get("/candidates", params=params, paginate=paginate)


async def get_candidate(
    client: GreenhouseClient,
    *,
    candidate_id: int,
) -> dict[str, Any]:
    """Get a single candidate by ID."""
    return await client.harvest_get_one(f"/candidates/{candidate_id}")


async def create_candidate(
    client: GreenhouseClient,
    *,
    first_name: str,
    last_name: str,
    company: str | None = None,
    title: str | None = None,
    phone_numbers: list[dict[str, Any]] | None = None,
    email_addresses: list[dict[str, Any]] | None = None,
    addresses: list[dict[str, Any]] | None = None,
    tags: list[str] | None = None,
    custom_fields: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a new candidate with name and optional company, title, phone, email, tags."""
    json_data: dict[str, Any] = {"first_name": first_name, "last_name": last_name}
    if company is not None:
        json_data["company"] = company
    if title is not None:
        json_data["title"] = title
    if phone_numbers is not None:
        json_data["phone_numbers"] = phone_numbers
    if email_addresses is not None:
        json_data["email_addresses"] = email_addresses
    if addresses is not None:
        json_data["addresses"] = addresses
    if tags is not None:
        json_data["tags"] = tags
    if custom_fields is not None:
        json_data["custom_fields"] = custom_fields
    return await client.harvest_post("/candidates", json_data=json_data)


async def update_candidate(
    client: GreenhouseClient,
    *,
    candidate_id: int,
    first_name: str | None = None,
    last_name: str | None = None,
    company: str | None = None,
    title: str | None = None,
    phone_numbers: list[dict[str, Any]] | None = None,
    email_addresses: list[dict[str, Any]] | None = None,
    tags: list[str] | None = None,
    custom_fields: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Update a candidate's name, company, title, phone, email, tags, or custom fields by ID."""
    json_data: dict[str, Any] = {}
    if first_name is not None:
        json_data["first_name"] = first_name
    if last_name is not None:
        json_data["last_name"] = last_name
    if company is not None:
        json_data["company"] = company
    if title is not None:
        json_data["title"] = title
    if phone_numbers is not None:
        json_data["phone_numbers"] = phone_numbers
    if email_addresses is not None:
        json_data["email_addresses"] = email_addresses
    if tags is not None:
        json_data["tags"] = tags
    if custom_fields is not None:
        json_data["custom_fields"] = custom_fields
    return await client.harvest_patch(f"/candidates/{candidate_id}", json_data=json_data)


async def delete_candidate(
    client: GreenhouseClient,
    *,
    candidate_id: int,
) -> dict[str, Any]:
    """Delete a candidate by ID."""
    return await client.harvest_delete(f"/candidates/{candidate_id}")


async def merge_candidates(
    client: GreenhouseClient,
    *,
    primary_candidate_id: int,
    duplicate_candidate_id: int,
) -> dict[str, Any]:
    """Merge a duplicate candidate into a primary candidate, preserving the primary's record."""
    json_data: dict[str, Any] = {
        "primary_candidate_id": primary_candidate_id,
        "duplicate_candidate_id": duplicate_candidate_id,
    }
    return await client.harvest_put("/candidates/merge", json_data=json_data)


async def anonymize_candidate(
    client: GreenhouseClient,
    *,
    candidate_id: int,
    fields: list[str] | None = None,
) -> dict[str, Any]:
    """Anonymize specific fields on a candidate for GDPR/privacy compliance."""
    json_data: dict[str, Any] = {}
    if fields is not None:
        json_data["fields"] = fields
    return await client.harvest_put(
        f"/candidates/{candidate_id}/anonymize", json_data=json_data or None
    )


async def add_prospect(
    client: GreenhouseClient,
    *,
    first_name: str,
    last_name: str,
    company: str | None = None,
    title: str | None = None,
    phone_numbers: list[dict[str, Any]] | None = None,
    email_addresses: list[dict[str, Any]] | None = None,
    prospect_pool_id: int | None = None,
    prospect_stage_id: int | None = None,
    prospect_owner_id: int | None = None,
) -> dict[str, Any]:
    """Create a new prospect with name and optional pool, stage, and owner assignment."""
    json_data: dict[str, Any] = {
        "first_name": first_name,
        "last_name": last_name,
        "is_prospect": True,
    }
    if company is not None:
        json_data["company"] = company
    if title is not None:
        json_data["title"] = title
    if phone_numbers is not None:
        json_data["phone_numbers"] = phone_numbers
    if email_addresses is not None:
        json_data["email_addresses"] = email_addresses
    if prospect_pool_id is not None:
        json_data["prospect_pool_id"] = prospect_pool_id
    if prospect_stage_id is not None:
        json_data["prospect_stage_id"] = prospect_stage_id
    if prospect_owner_id is not None:
        json_data["prospect_owner_id"] = prospect_owner_id
    return await client.harvest_post("/candidates", json_data=json_data)


async def add_education(
    client: GreenhouseClient,
    *,
    candidate_id: int,
    school_id: int | None = None,
    discipline_id: int | None = None,
    degree_id: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Add an education record to a candidate with school, discipline, degree, dates."""
    json_data: dict[str, Any] = {}
    if school_id is not None:
        json_data["school_id"] = school_id
    if discipline_id is not None:
        json_data["discipline_id"] = discipline_id
    if degree_id is not None:
        json_data["degree_id"] = degree_id
    if start_date is not None:
        json_data["start_date"] = start_date
    if end_date is not None:
        json_data["end_date"] = end_date
    return await client.harvest_post(
        f"/candidates/{candidate_id}/educations", json_data=json_data
    )


async def remove_education(
    client: GreenhouseClient,
    *,
    candidate_id: int,
    education_id: int,
) -> dict[str, Any]:
    """Remove an education record from a candidate."""
    return await client.harvest_delete(
        f"/candidates/{candidate_id}/educations/{education_id}"
    )


async def add_employment(
    client: GreenhouseClient,
    *,
    candidate_id: int,
    company_name: str | None = None,
    title: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Add an employment history record to a candidate with optional company, title, and dates."""
    json_data: dict[str, Any] = {}
    if company_name is not None:
        json_data["company_name"] = company_name
    if title is not None:
        json_data["title"] = title
    if start_date is not None:
        json_data["start_date"] = start_date
    if end_date is not None:
        json_data["end_date"] = end_date
    return await client.harvest_post(
        f"/candidates/{candidate_id}/employments", json_data=json_data
    )


async def remove_employment(
    client: GreenhouseClient,
    *,
    candidate_id: int,
    employment_id: int,
) -> dict[str, Any]:
    """Remove an employment history record from a candidate."""
    return await client.harvest_delete(
        f"/candidates/{candidate_id}/employments/{employment_id}"
    )


async def add_attachment(
    client: GreenhouseClient,
    *,
    candidate_id: int,
    filename: str,
    type: str,
    content: str | None = None,
    url: str | None = None,
    content_type: str = "application/pdf",
) -> dict[str, Any]:
    """Attach a file (resume, cover letter, etc.) to a candidate via base64 content or URL."""
    json_data: dict[str, Any] = {"filename": filename, "type": type, "content_type": content_type}
    if content is not None:
        json_data["content"] = content
    if url is not None:
        json_data["url"] = url
    return await client.harvest_post(
        f"/candidates/{candidate_id}/attachments", json_data=json_data
    )


async def add_note_to_candidate(
    client: GreenhouseClient,
    *,
    candidate_id: int,
    body: str,
    visibility: str = "private",
) -> dict[str, Any]:
    """Add a text note to a candidate's activity feed with optional visibility (private/public)."""
    json_data: dict[str, Any] = {"body": body, "visibility": visibility}
    return await client.harvest_post(
        f"/candidates/{candidate_id}/activity_feed/notes", json_data=json_data
    )


async def add_email_note_to_candidate(
    client: GreenhouseClient,
    *,
    candidate_id: int,
    to: str,
    from_: str,
    subject: str,
    body: str,
) -> dict[str, Any]:
    """Log an email interaction on a candidate's activity feed with to, from, subject, and body."""
    json_data: dict[str, Any] = {"to": to, "from": from_, "subject": subject, "body": body}
    return await client.harvest_post(
        f"/candidates/{candidate_id}/activity_feed/emails", json_data=json_data
    )
