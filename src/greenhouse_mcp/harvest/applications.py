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
    candidate_id: Annotated[
        int | None, Field(description="Filter to applications for this candidate")
    ] = None,
    status: Annotated[
        str | None, Field(description="Filter by status: 'active', 'rejected', or 'hired'")
    ] = None,
    created_after: Annotated[
        str | None, Field(description="ISO 8601 datetime — only applications created after this")
    ] = None,
    created_before: Annotated[
        str | None, Field(description="ISO 8601 datetime — only applications created before this")
    ] = None,
    last_activity_after: Annotated[
        str | None,
        Field(description="ISO 8601 datetime — only applications with activity after this"),
    ] = None,
    paginate: Annotated[
        str, Field(description="'single' for one page, 'all' to auto-fetch every page")
    ] = "single",
) -> dict[str, Any]:
    """List applications with optional filters. Read-only.

    Users say "show me applications for [job name]" or "what came in this week."
    To filter by job: list_jobs → find by name → use its job_id. To filter by
    candidate: search_candidates_by_name → candidate_id. For pipeline views
    grouped by stage, use pipeline_summary. For stale candidates, use
    stale_applications or candidates_needing_action.
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
    """Get a single application by ID. Read-only.

    Users rarely know application IDs. To find one: search_candidates_by_name →
    get_candidate → the applications array has each application's ID and job name.
    For a complete screening package with resume and location, use screen_candidate.
    """
    return await client.harvest_get_one(f"/applications/{application_id}")


async def create_application(
    client: GreenhouseClient,
    *,
    candidate_id: Annotated[
        int, Field(description="ID of an existing candidate — use create_candidate first if needed")
    ],
    job_id: Annotated[int, Field(description="ID of the job to apply to — get from list_jobs")],
    source_id: Annotated[
        int | None, Field(description="Candidate source ID — get from list_sources")
    ] = None,
    referrer: Annotated[
        dict[str, Any] | None,
        Field(
            description="Referrer: {type:'id', value:user_id} or {type:'outside',...}"
        ),
    ] = None,
    initial_stage_id: Annotated[
        int | None,
        Field(description="Starting pipeline stage — defaults to first stage if omitted"),
    ] = None,
    attachments: Annotated[
        list[dict[str, Any]] | None,
        Field(description="Resume/files: [{filename, type, content (base64), content_type}]"),
    ] = None,
) -> dict[str, Any]:
    """Apply an existing candidate to a job. Write operation.

    Users say "add Sarah to the Backend Engineer role." Resolve both IDs first:
    candidate — search_candidates_by_name; job — list_jobs → match by name.
    The candidate must already exist (create_candidate first if needed). For
    sourced prospects, use add_prospect. For partner submissions, use post_candidate.
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
    source_id: Annotated[
        int | None, Field(description="New source ID — get from list_sources")
    ] = None,
    referrer: Annotated[
        dict[str, Any] | None, Field(description="Referrer object: {type: 'id', value: user_id}")
    ] = None,
    custom_fields: Annotated[
        list[dict[str, Any]] | None,
        Field(
            description="Array of {id, value} — get field IDs from list_custom_fields"
        ),
    ] = None,
) -> dict[str, Any]:
    """Update an application's source, referrer, or custom fields. Write operation.

    To find the application_id: search_candidates_by_name → get_candidate →
    match the application to the job. Only updates fields you provide.
    For source_id: list_sources. For custom field IDs: list_custom_fields.
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

    To find the application_id: search_candidates_by_name → get_candidate →
    match the application to the job. Consider reject_application instead —
    it preserves history and can be reversed with unreject_application.
    """
    return await client.harvest_delete(f"/applications/{application_id}")


async def advance_application(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
    from_stage_id: Annotated[
        int,
        Field(
            description="Current stage ID — from list_job_stages_for_job or get_application"
        ),
    ],
    to_stage_id: Annotated[
        int | None,
        Field(
            description="Target stage — from list_job_stages_for_job. Omit for next stage"
        ),
    ] = None,
) -> dict[str, Any]:
    """Move a candidate forward one stage in their job pipeline. Write operation.

    Users say "advance Sarah to the next stage" or "move John forward."
    To get the application_id: search_candidates_by_name → get_candidate →
    match the application to the job. Stage IDs are optional — omit to
    advance to the natural next stage. To skip stages, use move_application_same_job.
    For bulk advancing, use bulk_advance.
    """
    json_data: dict[str, Any] = {"from_stage_id": from_stage_id}
    if to_stage_id is not None:
        json_data["to_stage_id"] = to_stage_id
    return await client.harvest_post(f"/applications/{application_id}/advance", json_data=json_data)


async def move_application(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
    new_job_id: Annotated[int, Field(description="Target job ID — get from list_jobs")],
    new_stage_id: Annotated[
        int | None,
        Field(description="Target stage in new job — defaults to first stage if omitted"),
    ] = None,
) -> dict[str, Any]:
    """Transfer a candidate to a completely different job. Write operation.

    Users say "move Sarah from Backend to Frontend Engineer." You need the
    application_id (search_candidates_by_name → get_candidate → match app)
    and the new_job_id (list_jobs → match by name). Optionally set a starting
    stage with new_stage_id (list_job_stages_for_job on the target job).
    To move within the SAME job, use move_application_same_job instead.
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
    to_stage_id: Annotated[
        int,
        Field(description="Target stage ID within the same job — get from list_job_stages_for_job"),
    ],
) -> dict[str, Any]:
    """Skip a candidate to a specific stage within the same job. Write operation.

    Users say "move Sarah straight to the onsite stage" or "skip phone screen."
    To get the application_id: search_candidates_by_name → get_candidate →
    match app to job. For stage IDs: list_job_stages_for_job → find by name.
    To advance to just the next stage, use advance_application instead.
    """
    json_data: dict[str, Any] = {"from_stage_id": from_stage_id, "to_stage_id": to_stage_id}
    return await client.harvest_post(f"/applications/{application_id}/move", json_data=json_data)


async def reject_application(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
    rejection_reason_id: Annotated[
        int | None, Field(description="Reason ID — get from list_rejection_reasons")
    ] = None,
    notes: Annotated[
        str | None, Field(description="Internal rejection notes (not sent to candidate)")
    ] = None,
    rejection_email: Annotated[
        dict[str, Any] | None,
        Field(
            description="Optional email to candidate: {email_template_id, send_email_at (ISO 8601)}"
        ),
    ] = None,
) -> dict[str, Any]:
    """Reject a candidate from a job. Write operation.

    Users say "reject Sarah from the Backend role." To get the application_id:
    search_candidates_by_name → get_candidate → match the application to the
    job. For rejection_reason_id: list_rejection_reasons → match by name.
    For email templates: list_email_templates. Can be reversed with
    unreject_application. For bulk rejections, use bulk_reject.
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
    application_id: Annotated[
        int, Field(description="Greenhouse application ID of a rejected application")
    ],
) -> dict[str, Any]:
    """Reverse a rejection, returning the candidate to active status. Write operation.

    Users say "undo the rejection for Sarah" or "bring Sarah back." To get the
    application_id: search_candidates_by_name → get_candidate → find the
    rejected application in their applications array.
    """
    return await client.harvest_post(f"/applications/{application_id}/unreject")


async def update_rejection_reason(
    client: GreenhouseClient,
    *,
    application_id: Annotated[
        int, Field(description="Greenhouse application ID (must be already rejected)")
    ],
    rejection_reason_id: Annotated[
        int, Field(description="New rejection reason ID — get from list_rejection_reasons")
    ],
) -> dict[str, Any]:
    """Change the rejection reason on an already-rejected application. Write operation.

    To find the application_id: search_candidates_by_name → get_candidate →
    find the rejected application. For the new reason: list_rejection_reasons
    → match by name.
    """
    json_data: dict[str, Any] = {"rejection_reason_id": rejection_reason_id}
    return await client.harvest_patch(f"/applications/{application_id}/reject", json_data=json_data)


async def hire_application(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
    start_date: Annotated[str | None, Field(description="Hire start date as 'YYYY-MM-DD'")] = None,
    opening_id: Annotated[
        int | None, Field(description="Job opening to fill — get from list_job_openings")
    ] = None,
    close_reason_id: Annotated[
        int | None,
        Field(description="Reason for closing the opening — get from list_close_reasons"),
    ] = None,
) -> dict[str, Any]:
    """Mark a candidate as hired. Write operation — finalizes the hiring decision.

    Users say "hire Sarah for the Backend role." To get the application_id:
    search_candidates_by_name → get_candidate → match the application to the
    job. Optionally fills a job opening (opening_id from list_job_openings)
    and records a close reason (close_reason_id from list_close_reasons).
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
    job_id: Annotated[
        int, Field(description="Job ID to apply the prospect to — get from list_jobs")
    ],
) -> dict[str, Any]:
    """Convert a sourced prospect into an active candidate on a job. Write operation.

    Users say "move this prospect into the Backend pipeline." The prospect's
    application_id comes from their prospect record (get_candidate → applications
    array). Target job_id from list_jobs → match by name.
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
    type: Annotated[
        str,
        Field(
            description="Type: 'resume', 'cover_letter', 'admin_only', or 'take_home_test'"
        ),
    ],
    content: Annotated[
        str | None, Field(description="Base64-encoded file content — provide this OR url, not both")
    ] = None,
    url: Annotated[
        str | None,
        Field(description="Public URL to fetch the file from — provide this OR content, not both"),
    ] = None,
    content_type: Annotated[
        str, Field(description="MIME type, e.g. 'application/pdf', 'application/msword'")
    ] = "application/pdf",
) -> dict[str, Any]:
    """Attach a file to a specific application. Write operation.

    To find the application_id: search_candidates_by_name → get_candidate →
    match the application to the job. To attach to the candidate record instead
    (shared across all their applications), use add_attachment.
    """
    json_data: dict[str, Any] = {"filename": filename, "type": type, "content_type": content_type}
    if content is not None:
        json_data["content"] = content
    if url is not None:
        json_data["url"] = url
    return await client.harvest_post(
        f"/applications/{application_id}/attachments", json_data=json_data
    )
