"""Harvest API — Applications tools (14 tools)."""
from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_applications(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    job_id: int | None = None,
    candidate_id: int | None = None,
    status: str | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
    last_activity_after: str | None = None,
    paginate: str = "single",
) -> dict[str, Any]:
    """List all applications with optional filters for job, candidate, status, dates."""
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    if job_id is not None:
        params["job_id"] = job_id
    if candidate_id is not None:
        params["candidate_id"] = candidate_id
    if status is not None:
        params["status"] = status
    if created_after is not None:
        params["created_after"] = created_after
    if created_before is not None:
        params["created_before"] = created_before
    if last_activity_after is not None:
        params["last_activity_after"] = last_activity_after
    return await client.harvest_get("/applications", params=params, paginate=paginate)


async def get_application(
    client: GreenhouseClient,
    *,
    application_id: int,
) -> dict[str, Any]:
    """Get a single application by ID."""
    return await client.harvest_get_one(f"/applications/{application_id}")


async def create_application(
    client: GreenhouseClient,
    *,
    candidate_id: int,
    job_id: int,
    source_id: int | None = None,
    referrer: dict[str, Any] | None = None,
    initial_stage_id: int | None = None,
    attachments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create an application for a candidate on a job with optional source and referrer."""
    json_data: dict[str, Any] = {"job_id": job_id}
    if source_id is not None:
        json_data["source_id"] = source_id
    if referrer is not None:
        json_data["referrer"] = referrer
    if initial_stage_id is not None:
        json_data["initial_stage_id"] = initial_stage_id
    if attachments is not None:
        json_data["attachments"] = attachments
    return await client.harvest_post(
        f"/candidates/{candidate_id}/applications", json_data=json_data
    )


async def update_application(
    client: GreenhouseClient,
    *,
    application_id: int,
    source_id: int | None = None,
    referrer: dict[str, Any] | None = None,
    custom_fields: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Update an application's source, referrer, or custom fields."""
    json_data: dict[str, Any] = {}
    if source_id is not None:
        json_data["source_id"] = source_id
    if referrer is not None:
        json_data["referrer"] = referrer
    if custom_fields is not None:
        json_data["custom_fields"] = custom_fields
    return await client.harvest_patch(f"/applications/{application_id}", json_data=json_data)


async def delete_application(
    client: GreenhouseClient,
    *,
    application_id: int,
) -> dict[str, Any]:
    """Delete an application by ID."""
    return await client.harvest_delete(f"/applications/{application_id}")


async def advance_application(
    client: GreenhouseClient,
    *,
    application_id: int,
    from_stage_id: int,
    to_stage_id: int | None = None,
) -> dict[str, Any]:
    """Advance an application from a given stage to the next stage or a specified target stage."""
    json_data: dict[str, Any] = {"from_stage_id": from_stage_id}
    if to_stage_id is not None:
        json_data["to_stage_id"] = to_stage_id
    return await client.harvest_post(
        f"/applications/{application_id}/advance", json_data=json_data
    )


async def move_application(
    client: GreenhouseClient,
    *,
    application_id: int,
    new_job_id: int,
    new_stage_id: int | None = None,
) -> dict[str, Any]:
    """Transfer an application to a different job, optionally placing it at a specific stage."""
    json_data: dict[str, Any] = {"new_job_id": new_job_id}
    if new_stage_id is not None:
        json_data["new_stage_id"] = new_stage_id
    return await client.harvest_post(
        f"/applications/{application_id}/transfer_to_job", json_data=json_data
    )


async def move_application_same_job(
    client: GreenhouseClient,
    *,
    application_id: int,
    from_stage_id: int,
    to_stage_id: int,
) -> dict[str, Any]:
    """Move an application between stages within the same job."""
    json_data: dict[str, Any] = {"from_stage_id": from_stage_id, "to_stage_id": to_stage_id}
    return await client.harvest_post(
        f"/applications/{application_id}/move", json_data=json_data
    )


async def reject_application(
    client: GreenhouseClient,
    *,
    application_id: int,
    rejection_reason_id: int | None = None,
    notes: str | None = None,
    rejection_email: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Reject an application with an optional rejection reason, notes, and rejection email."""
    json_data: dict[str, Any] = {}
    if rejection_reason_id is not None:
        json_data["rejection_reason_id"] = rejection_reason_id
    if notes is not None:
        json_data["notes"] = notes
    if rejection_email is not None:
        json_data["rejection_email"] = rejection_email
    return await client.harvest_post(
        f"/applications/{application_id}/reject", json_data=json_data or None
    )


async def unreject_application(
    client: GreenhouseClient,
    *,
    application_id: int,
) -> dict[str, Any]:
    """Unreject a previously rejected application, returning it to active status."""
    return await client.harvest_post(f"/applications/{application_id}/unreject")


async def update_rejection_reason(
    client: GreenhouseClient,
    *,
    application_id: int,
    rejection_reason_id: int,
) -> dict[str, Any]:
    """Update the rejection reason on an already-rejected application."""
    json_data: dict[str, Any] = {"rejection_reason_id": rejection_reason_id}
    return await client.harvest_patch(
        f"/applications/{application_id}/reject", json_data=json_data
    )


async def hire_application(
    client: GreenhouseClient,
    *,
    application_id: int,
    start_date: str | None = None,
    opening_id: int | None = None,
    close_reason_id: int | None = None,
) -> dict[str, Any]:
    """Mark an application as hired with optional start date, opening, and close reason."""
    json_data: dict[str, Any] = {}
    if start_date is not None:
        json_data["start_date"] = start_date
    if opening_id is not None:
        json_data["opening_id"] = opening_id
    if close_reason_id is not None:
        json_data["close_reason_id"] = close_reason_id
    return await client.harvest_post(
        f"/applications/{application_id}/hire", json_data=json_data or None
    )


async def convert_prospect(
    client: GreenhouseClient,
    *,
    application_id: int,
    job_id: int,
) -> dict[str, Any]:
    """Convert a prospect application to a candidate application on a specific job."""
    json_data: dict[str, Any] = {"job_id": job_id}
    return await client.harvest_patch(
        f"/applications/{application_id}/convert_to_candidate", json_data=json_data
    )


async def add_attachment_to_application(
    client: GreenhouseClient,
    *,
    application_id: int,
    filename: str,
    type: str,
    content: str | None = None,
    url: str | None = None,
    content_type: str = "application/pdf",
) -> dict[str, Any]:
    """Attach a file to an application via base64 content or URL."""
    json_data: dict[str, Any] = {"filename": filename, "type": type, "content_type": content_type}
    if content is not None:
        json_data["content"] = content
    if url is not None:
        json_data["url"] = url
    return await client.harvest_post(
        f"/applications/{application_id}/attachments", json_data=json_data
    )
