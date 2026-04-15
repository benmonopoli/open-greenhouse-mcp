"""Harvest API — Applications tools (14 tools)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_applications(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    page: Annotated[int, Field(description="Page number (starts at 1)")] = 1,
    job_id: Annotated[int | None, Field(description="Filter to applications on this job")] = None,
    candidate_id: Annotated[int | None, Field(description="Filter to applications for this candidate")] = None,
    status: Annotated[str | None, Field(description="Filter by status: 'active', 'rejected', or 'hired'")] = None,
    created_after: Annotated[str | None, Field(description="ISO 8601 datetime — only applications created after this")] = None,
    created_before: Annotated[str | None, Field(description="ISO 8601 datetime — only applications created before this")] = None,
    last_activity_after: Annotated[str | None, Field(description="ISO 8601 datetime — only applications with activity after this")] = None,
    paginate: Annotated[str, Field(description="'single' for one page, 'all' to auto-fetch every page")] = "single",
) -> dict[str, Any]:
    """List applications with optional filters. Read-only. Default returns one page of 500.

    Set paginate="all" to auto-fetch every page. Filters: job_id, candidate_id,
    status ("active"/"rejected"/"hired"), date ranges. For pipeline views with candidates
    grouped by stage, use pipeline_summary instead. For finding stale candidates, use
    stale_applications or candidates_needing_action. For conversion metrics, use pipeline_metrics.
    """
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
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
) -> dict[str, Any]:
    """Get a single application by ID. Read-only. Returns the full application record
    including candidate ID, job ID, current stage, status, source, and rejection details.

    Use when you have an application_id. To find applications by job or candidate,
    use list_applications with job_id or candidate_id filters. For a complete candidate
    screening package, use screen_candidate instead.
    """
    return await client.harvest_get_one(f"/applications/{application_id}")


async def create_application(
    client: GreenhouseClient,
    *,
    candidate_id: Annotated[int, Field(description="ID of an existing candidate — use create_candidate first if needed")],
    job_id: Annotated[int, Field(description="ID of the job to apply to — get from list_jobs")],
    source_id: Annotated[int | None, Field(description="Candidate source ID — get from list_sources")] = None,
    referrer: Annotated[dict[str, Any] | None, Field(description="Referrer object: {type: 'id', value: user_id} or {type: 'outside', first_name, last_name}")] = None,
    initial_stage_id: Annotated[int | None, Field(description="Starting pipeline stage — defaults to first stage if omitted")] = None,
    attachments: Annotated[list[dict[str, Any]] | None, Field(description="Resume/files: [{filename, type, content (base64), content_type}]")] = None,
) -> dict[str, Any]:
    """Add an existing candidate to a job. Write operation — creates a new application record.

    Use this to apply a candidate to a job. The candidate must already exist (use
    create_candidate first). For sourced prospects, use add_prospect instead. For
    external/partner submissions, use the Ingestion API's post_candidate.
    """
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
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
    source_id: Annotated[int | None, Field(description="New source ID — get from list_sources")] = None,
    referrer: Annotated[dict[str, Any] | None, Field(description="Referrer object: {type: 'id', value: user_id}")] = None,
    custom_fields: Annotated[list[dict[str, Any]] | None, Field(description="Array of {id: field_id, value: ...} — get field IDs from list_custom_fields")] = None,
) -> dict[str, Any]:
    """Update an application's source, referrer, or custom fields. Write operation.

    Only updates the fields you provide — omitted fields are unchanged. To change
    pipeline stage, use advance_application or move_application_same_job instead.
    To reject, use reject_application. To hire, use hire_application.
    """
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
    application_id: Annotated[int, Field(description="Greenhouse application ID to delete")],
) -> dict[str, Any]:
    """Permanently delete an application. Destructive — cannot be undone.

    This removes the application and all associated data (scorecards, scheduled
    interviews, activity). Use reject_application instead if you want to preserve
    the record. Only use delete for test data or duplicate applications.
    """
    return await client.harvest_delete(f"/applications/{application_id}")


async def advance_application(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
    from_stage_id: Annotated[int, Field(description="Candidate's current stage ID — get from list_job_stages_for_job or get_application")],
    to_stage_id: Annotated[int | None, Field(description="Target stage ID — omit to advance to next sequential stage")] = None,
) -> dict[str, Any]:
    """Advance an application to the NEXT stage in the pipeline (within the same job).
    Write operation — changes the candidate's pipeline position.

    Use this to move a candidate forward one step, e.g. from "Phone Screen" to "Onsite".
    Requires from_stage_id (the candidate's current stage). If to_stage_id is omitted,
    advances to the next sequential stage. For moving between arbitrary stages in the
    same job, use move_application_same_job instead. For transferring to a different
    job entirely, use move_application.
    """
    json_data: dict[str, Any] = {"from_stage_id": from_stage_id}
    if to_stage_id is not None:
        json_data["to_stage_id"] = to_stage_id
    return await client.harvest_post(
        f"/applications/{application_id}/advance", json_data=json_data
    )


async def move_application(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
    new_job_id: Annotated[int, Field(description="Target job ID — get from list_jobs")],
    new_stage_id: Annotated[int | None, Field(description="Target stage in new job — defaults to first stage if omitted")] = None,
) -> dict[str, Any]:
    """Transfer an application to a DIFFERENT JOB entirely. Write operation — moves
    the candidate out of their current job pipeline into a new one.

    Use this when a candidate is a better fit for a different role. The application
    leaves the original job. For moving between stages within the SAME job, use
    move_application_same_job or advance_application instead.
    """
    json_data: dict[str, Any] = {"new_job_id": new_job_id}
    if new_stage_id is not None:
        json_data["new_stage_id"] = new_stage_id
    return await client.harvest_post(
        f"/applications/{application_id}/transfer_to_job", json_data=json_data
    )


async def move_application_same_job(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
    from_stage_id: Annotated[int, Field(description="Candidate's current stage ID")],
    to_stage_id: Annotated[int, Field(description="Target stage ID within the same job — get from list_job_stages_for_job")],
) -> dict[str, Any]:
    """Move an application to a SPECIFIC stage within the SAME job (skip stages).
    Write operation — changes the candidate's pipeline position.

    Use this to jump to any stage (forward or backward) within the same job, e.g.
    move from "Onsite" back to "Phone Screen". For sequential advancement to the
    next stage, use advance_application instead. For transferring to a different
    job, use move_application.
    """
    json_data: dict[str, Any] = {"from_stage_id": from_stage_id, "to_stage_id": to_stage_id}
    return await client.harvest_post(
        f"/applications/{application_id}/move", json_data=json_data
    )


async def reject_application(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
    rejection_reason_id: Annotated[int | None, Field(description="Reason ID — get from list_rejection_reasons")] = None,
    notes: Annotated[str | None, Field(description="Internal rejection notes (not sent to candidate)")] = None,
    rejection_email: Annotated[dict[str, Any] | None, Field(description="Optional email to candidate: {email_template_id, send_email_at (ISO 8601)}")] = None,
) -> dict[str, Any]:
    """Reject a single application. Write operation — marks the candidate as rejected
    on this job. Optionally sends a rejection email to the candidate.

    Can be reversed with unreject_application. For bulk rejections, use bulk_reject.
    To update the reason on an already-rejected application, use update_rejection_reason.
    Get available reasons from list_rejection_reasons and email templates from
    list_email_templates.
    """
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
    application_id: Annotated[int, Field(description="Greenhouse application ID of a rejected application")],
) -> dict[str, Any]:
    """Unreject a previously rejected application, returning it to active status.
    Write operation — reverses a rejection.

    The application returns to the stage it was in before rejection. Use this to
    reactivate candidates who were rejected in error or whose circumstances changed.
    Only works on rejected applications — active or hired applications cannot be unrejected.
    """
    return await client.harvest_post(f"/applications/{application_id}/unreject")


async def update_rejection_reason(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID (must be already rejected)")],
    rejection_reason_id: Annotated[int, Field(description="New rejection reason ID — get from list_rejection_reasons")],
) -> dict[str, Any]:
    """Update the rejection reason on an already-rejected application. Write operation.

    Only works on applications that have already been rejected via reject_application.
    Use this to correct or refine the rejection reason. Get available reasons from
    list_rejection_reasons. To reverse the rejection entirely, use unreject_application.
    """
    json_data: dict[str, Any] = {"rejection_reason_id": rejection_reason_id}
    return await client.harvest_patch(
        f"/applications/{application_id}/reject", json_data=json_data
    )


async def hire_application(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
    start_date: Annotated[str | None, Field(description="Hire start date as 'YYYY-MM-DD'")] = None,
    opening_id: Annotated[int | None, Field(description="Job opening to fill — get from list_job_openings")] = None,
    close_reason_id: Annotated[int | None, Field(description="Reason for closing the opening — get from list_close_reasons")] = None,
) -> dict[str, Any]:
    """Mark an application as hired. Write operation — finalizes the hiring decision
    and optionally fills a job opening.

    This is typically the last step in the pipeline after offer acceptance. If
    opening_id is provided, that opening is closed. Use advance_application to move
    candidates through earlier pipeline stages. Get available openings from
    list_job_openings and close reasons from list_close_reasons.
    """
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
    application_id: Annotated[int, Field(description="Prospect application ID to convert")],
    job_id: Annotated[int, Field(description="Job ID to apply the prospect to — get from list_jobs")],
) -> dict[str, Any]:
    """Convert a prospect application to a candidate application on a specific job.
    Write operation — moves a sourced prospect into an active job pipeline.

    Prospects are created via add_prospect and live in prospect pools. Use this when
    a prospect is ready to enter a job's hiring pipeline. The prospect's data is
    preserved. For creating a brand-new application (not from a prospect), use
    create_application instead.
    """
    json_data: dict[str, Any] = {"job_id": job_id}
    return await client.harvest_patch(
        f"/applications/{application_id}/convert_to_candidate", json_data=json_data
    )


async def add_attachment_to_application(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
    filename: Annotated[str, Field(description="File name with extension, e.g. 'resume.pdf'")],
    type: Annotated[str, Field(description="Attachment type: 'resume', 'cover_letter', 'admin_only', or 'take_home_test'")],
    content: Annotated[str | None, Field(description="Base64-encoded file content — provide this OR url, not both")] = None,
    url: Annotated[str | None, Field(description="Public URL to fetch the file from — provide this OR content, not both")] = None,
    content_type: Annotated[str, Field(description="MIME type, e.g. 'application/pdf', 'application/msword'")] = "application/pdf",
) -> dict[str, Any]:
    """Attach a file to a specific application. Write operation.

    Provide either base64 content OR a public URL (not both). To attach to the
    candidate record instead (shared across all their applications), use add_attachment.
    To read existing attachments, use read_candidate_resume or download_attachment.
    """
    json_data: dict[str, Any] = {"filename": filename, "type": type, "content_type": content_type}
    if content is not None:
        json_data["content"] = content
    if url is not None:
        json_data["url"] = url
    return await client.harvest_post(
        f"/applications/{application_id}/attachments", json_data=json_data
    )
