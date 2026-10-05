"""Harvest API — Applications tools (14 tools).

Also holds small private helpers shared by the other Group A modules (candidates,
attachments) for batched lookups and v3 request shaping.
"""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient, add_date_filter, normalize_datetime

# ---------------------------------------------------------------------------
# Private helpers (not registered as tools — names start with "_")
# ---------------------------------------------------------------------------

_ATTACHMENT_TYPES = (
    "resume",
    "cover_letter",
    "take_home_test",
    "offer_packet",
    "offer_letter",
    "signed_offer_letter",
    "other",
    "form_attachment",
    "midfunnel_agreement",
    "automated_agreement",
)


def _invalid(message: str, **extra: Any) -> dict[str, Any]:
    """A client-side validation error in the same shape as API errors."""
    result: dict[str, Any] = {"error": message, "status_code": 400}
    result.update(extra)
    return result


async def _lookup(
    client: GreenhouseClient,
    endpoint: str,
    ids: Any,
    warnings: list[str],
    *,
    filter_name: str = "ids",
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Batched fetch of ``endpoint`` filtered by ``filter_name`` (50 ids per call).

    On failure, records a warning and returns [] so callers can degrade gracefully.
    """
    wanted = {i for i in ids if isinstance(i, int)}
    if not wanted:
        return []
    result = await client.harvest_get_ids(endpoint, filter_name, wanted, params=params)
    if client._is_error(result):
        warnings.append(
            f"Could not load {endpoint} ({result.get('status_code')}): {result.get('error')}"
        )
        return []
    return list(result.get("items", []))


def _by_id(items: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {i["id"]: i for i in items if isinstance(i, dict) and "id" in i}


def _with_warnings(result: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    if warnings:
        result["warnings"] = warnings
    return result


def _v3_custom_fields(custom_fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Accept v1-style ``{id, value}`` entries and convert to v3 ``{custom_field_id, value}``.

    Entries already using ``custom_field_id`` or ``name_key`` pass through unchanged.
    """
    out: list[dict[str, Any]] = []
    for cf in custom_fields:
        entry = dict(cf)
        if "custom_field_id" not in entry and "name_key" not in entry and "id" in entry:
            entry["custom_field_id"] = entry.pop("id")
        out.append(entry)
    return out


async def _add_job_names(
    client: GreenhouseClient, applications: list[dict[str, Any]], warnings: list[str]
) -> None:
    """Add ``job_name`` to each application (one batched /jobs call), in place."""
    jobs = _by_id(await _lookup(client, "/jobs", {a.get("job_id") for a in applications}, warnings))
    for app in applications:
        job_id = app.get("job_id")
        app["job_name"] = jobs.get(job_id, {}).get("name") if job_id is not None else None


def _attachment_body(
    application_id: int,
    filename: str,
    type: str,
    content: str | None,
    url: str | None,
    visibility: str | None,
) -> dict[str, Any]:
    """Build a POST /v3/attachments body, or a validation error dict.

    v1's ``admin_only`` attachment type became a visibility in v3, so it maps to
    ``type='other', visibility='admin_only'``.
    """
    if (content is None) == (url is None):
        return _invalid("Provide exactly one of content (base64) or url.")
    if type == "admin_only":
        type, visibility = "other", visibility or "admin_only"
    if type not in _ATTACHMENT_TYPES:
        return _invalid(
            f"Unknown attachment type {type!r}.", valid_types=list(_ATTACHMENT_TYPES)
        )
    body: dict[str, Any] = {"application_id": application_id, "filename": filename, "type": type}
    if content is not None:
        body["content"] = content
    if url is not None:
        body["url"] = url
    if visibility is not None:
        body["visibility"] = visibility
    return body


async def _current_stage_id(client: GreenhouseClient, application_id: int) -> Any:
    """Return the application's current ``job_interview_stage_id`` (or an error dict)."""
    app = await client.harvest_get_by_id("/applications", application_id)
    if client._is_error(app):
        return app
    stage_id = app.get("job_interview_stage_id")
    if stage_id is None:
        return _invalid(
            "This application has no current interview stage (it may be a prospect, "
            "rejected, or hired), so it can't be moved.",
            application_id=application_id,
            status=app.get("status"),
        )
    return stage_id


async def _move_body(
    client: GreenhouseClient,
    application_id: int,
    from_stage_id: int | None,
    *,
    to_stage_id: int | None = None,
    to_job_id: int | None = None,
) -> dict[str, Any]:
    """Body for POST /v3/applications/{id}/move, resolving ``from_stage_id`` when omitted.

    Returns an error dict if the current stage can't be resolved. (Each move tool
    makes the POST itself so the server's write-tool detection sees it.)
    """
    if from_stage_id is None:
        resolved = await _current_stage_id(client, application_id)
        if client._is_error(resolved):
            return resolved  # type: ignore[no-any-return]
        from_stage_id = int(resolved)
    body: dict[str, Any] = {"from_stage_id": from_stage_id}
    if to_stage_id is not None:
        body["to_stage_id"] = to_stage_id
    if to_job_id is not None:
        body["to_job_id"] = to_job_id
    return body


def _done(result: dict[str, Any], **info: Any) -> dict[str, Any]:
    """Replace v3's empty 204 ``{"success": True}`` with a more informative summary."""
    if result == {"success": True}:
        return {"success": True, **info}
    return result


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


async def list_applications(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    cursor: Annotated[
        str | None,
        Field(description="Pass next_cursor from the previous response to get the next page"),
    ] = None,
    job_id: Annotated[int | None, Field(description="Filter to applications on this job")] = None,
    candidate_id: Annotated[
        int | None, Field(description="Filter to applications for this candidate")
    ] = None,
    status: Annotated[
        str | None,
        Field(description="Filter by status: 'active', 'rejected', 'hired', or 'converted'"),
    ] = None,
    created_after: Annotated[
        str | None,
        Field(description="ISO 8601 datetime — only applications created at/after this"),
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
    candidate: search_candidates_by_name → candidate_id. Each application has
    job_id + job_name, the current stage (stage_name, and job_interview_stage_id
    for moves), status ('in_process', 'rejected', 'hired', 'converted'),
    source_id, recruiter_id/coordinator_id, rejection_reason_id and created_at
    (the applied date). For pipeline views grouped by stage, use
    pipeline_summary. For stale candidates, use stale_applications or
    candidates_needing_action.
    """
    params: dict[str, Any] = {
        "per_page": per_page,
        "cursor": cursor,
        "job_ids": [job_id] if job_id is not None else None,
        "candidate_ids": [candidate_id] if candidate_id is not None else None,
        "status": status,
    }
    add_date_filter(params, "created_at", gte=created_after, lt=created_before)
    add_date_filter(params, "last_activity_at", gt=last_activity_after)
    result = await client.harvest_get("/applications", params=params, paginate=paginate)
    if client._is_error(result):
        return result
    warnings: list[str] = []
    await _add_job_names(client, result.get("items", []), warnings)
    return _with_warnings(result, warnings)


async def get_application(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
) -> dict[str, Any]:
    """Get a single application by ID. Read-only.

    Returns the application with job_name, its current stage (stage_name and
    job_interview_stage_id — the from_stage_id for moves), status, source_id,
    rejection_reason_id, custom fields, and its attachments (resume etc., with
    time-limited download URLs). Users rarely know application IDs. To find one:
    search_candidates_by_name → get_candidate → the applications array has each
    application's ID and job name. For a complete screening package with resume
    and location, use screen_candidate.
    """
    app = await client.harvest_get_by_id("/applications", application_id)
    if client._is_error(app):
        return app
    warnings: list[str] = []
    _, attachments = await asyncio.gather(
        _add_job_names(client, [app], warnings),
        _lookup(client, "/attachments", [application_id], warnings, filter_name="application_ids"),
    )
    app["attachments"] = attachments
    return _with_warnings(app, warnings)


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
    referrer_id: Annotated[
        int | None, Field(description="Referrer record ID to credit for this application")
    ] = None,
    recruiter_id: Annotated[
        int | None, Field(description="User ID of the recruiter — get from list_users")
    ] = None,
    coordinator_id: Annotated[
        int | None, Field(description="User ID of the coordinator — get from list_users")
    ] = None,
    initial_stage_id: Annotated[
        int | None,
        Field(
            description="Starting interview stage ID (list_job_stages_for_job) — defaults "
            "to the first stage"
        ),
    ] = None,
    attachments: Annotated[
        list[dict[str, Any]] | None,
        Field(
            description="Resume/files to add after creating: [{filename, type, content "
            "(base64) or url}]"
        ),
    ] = None,
) -> dict[str, Any]:
    """Apply an existing candidate to a job. Write operation.

    Users say "add Sarah to the Backend Engineer role." Resolve both IDs first:
    candidate — search_candidates_by_name; job — list_jobs → match by name.
    The candidate must already exist (create_candidate can also create the
    candidate and application in one step). Attachments are uploaded to the new
    application afterwards; their results are under attachment_results. For
    sourced prospects, use add_prospect. For partner submissions, use
    post_candidate.
    """
    json_data: dict[str, Any] = {"candidate_id": candidate_id, "job_id": job_id}
    for key, value in (
        ("source_id", source_id),
        ("referrer_id", referrer_id),
        ("recruiter_id", recruiter_id),
        ("coordinator_id", coordinator_id),
        ("initial_stage_id", initial_stage_id),
    ):
        if value is not None:
            json_data[key] = value
    result = await client.harvest_post("/applications", json_data=json_data)
    if client._is_error(result) or not attachments:
        return result
    application_id = result.get("id")
    uploads: list[dict[str, Any]] = []
    for att in attachments:
        body = _attachment_body(
            int(application_id or 0),
            str(att.get("filename", "")),
            str(att.get("type", "")),
            att.get("content"),
            att.get("url"),
            att.get("visibility"),
        )
        if client._is_error(body):
            uploads.append(body)
            continue
        uploads.append(await client.harvest_post("/attachments", json_data=body))
    result["attachment_results"] = uploads
    return result


async def update_application(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
    source_id: Annotated[
        int | None, Field(description="New source ID — get from list_sources")
    ] = None,
    referrer_id: Annotated[
        int | None, Field(description="Referrer record ID to credit for this application")
    ] = None,
    recruiter_id: Annotated[
        int | None, Field(description="User ID of the new recruiter — get from list_users")
    ] = None,
    coordinator_id: Annotated[
        int | None, Field(description="User ID of the new coordinator — get from list_users")
    ] = None,
    custom_fields: Annotated[
        list[dict[str, Any]] | None,
        Field(
            description="Array of {custom_field_id (or name_key), value} — get field IDs "
            "from list_custom_fields"
        ),
    ] = None,
) -> dict[str, Any]:
    """Update an application's source, referrer, recruiter, coordinator or custom fields.
    Write operation.

    To find the application_id: search_candidates_by_name → get_candidate →
    match the application to the job. Only updates fields you provide.
    For source_id: list_sources. For custom field IDs: list_custom_fields.
    To change a rejection reason, use update_rejection_reason.
    """
    json_data: dict[str, Any] = {}
    for key, value in (
        ("source_id", source_id),
        ("referrer_id", referrer_id),
        ("recruiter_id", recruiter_id),
        ("coordinator_id", coordinator_id),
    ):
        if value is not None:
            json_data[key] = value
    if custom_fields is not None:
        json_data["custom_fields"] = _v3_custom_fields(custom_fields)
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
        int | None,
        Field(
            description="Current job_interview_stage_id (from get_application). Omit to "
            "look it up automatically"
        ),
    ] = None,
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
    match the application to the job. from_stage_id must be the application's
    current job_interview_stage_id (Greenhouse rejects stale moves); omit it and
    it is looked up for you. Omit to_stage_id to advance to the natural next
    stage. To skip stages, use move_application_same_job. For bulk advancing,
    use bulk_advance.
    """
    body = await _move_body(client, application_id, from_stage_id, to_stage_id=to_stage_id)
    if client._is_error(body):
        return body
    result = await client.harvest_post(f"/applications/{application_id}/move", json_data=body)
    return _done(result, application_id=application_id, **body)


async def move_application(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
    new_job_id: Annotated[int, Field(description="Target job ID — get from list_jobs")],
    new_stage_id: Annotated[
        int | None,
        Field(description="Target stage in new job — defaults to first stage if omitted"),
    ] = None,
    from_stage_id: Annotated[
        int | None,
        Field(
            description="Current job_interview_stage_id (from get_application). Omit to "
            "look it up automatically"
        ),
    ] = None,
) -> dict[str, Any]:
    """Transfer a candidate to a completely different job. Write operation.

    Users say "move Sarah from Backend to Frontend Engineer." You need the
    application_id (search_candidates_by_name → get_candidate → match app)
    and the new_job_id (list_jobs → match by name). Optionally set a starting
    stage with new_stage_id (list_job_stages_for_job on the target job).
    The current stage is looked up automatically unless from_stage_id is given.
    To move within the SAME job, use move_application_same_job instead.
    """
    body = await _move_body(
        client, application_id, from_stage_id, to_stage_id=new_stage_id, to_job_id=new_job_id
    )
    if client._is_error(body):
        return body
    result = await client.harvest_post(f"/applications/{application_id}/move", json_data=body)
    return _done(result, application_id=application_id, **body)


async def move_application_same_job(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
    to_stage_id: Annotated[
        int,
        Field(description="Target stage ID within the same job — get from list_job_stages_for_job"),
    ],
    from_stage_id: Annotated[
        int | None,
        Field(
            description="Candidate's current job_interview_stage_id. Omit to look it up "
            "automatically"
        ),
    ] = None,
) -> dict[str, Any]:
    """Skip a candidate to a specific stage within the same job. Write operation.

    Users say "move Sarah straight to the onsite stage" or "skip phone screen."
    To get the application_id: search_candidates_by_name → get_candidate →
    match app to job. For stage IDs: list_job_stages_for_job → find by name.
    The current stage is looked up automatically unless from_stage_id is given.
    To advance to just the next stage, use advance_application instead.
    """
    body = await _move_body(client, application_id, from_stage_id, to_stage_id=to_stage_id)
    if client._is_error(body):
        return body
    result = await client.harvest_post(f"/applications/{application_id}/move", json_data=body)
    return _done(result, application_id=application_id, **body)


async def reject_application(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
    rejection_reason_id: Annotated[
        int, Field(description="Reason ID (required) — get from list_rejection_reasons")
    ],
    notes: Annotated[
        str | None, Field(description="Internal rejection notes (not sent to candidate)")
    ] = None,
    rejection_email: Annotated[
        dict[str, Any] | None,
        Field(
            description="Optional email to candidate: {email_template_id, send_email_at "
            "(ISO 8601), email_from_user_id}"
        ),
    ] = None,
) -> dict[str, Any]:
    """Reject a candidate from a job. Write operation.

    Users say "reject Sarah from the Backend role." To get the application_id:
    search_candidates_by_name → get_candidate → match the application to the
    job. A rejection_reason_id is required: list_rejection_reasons → match by
    name. For email templates: list_email_templates; the email is sent from
    email_from_user_id, defaulting to the configured Greenhouse user. Can be
    reversed with unreject_application. For bulk rejections, use bulk_reject.
    """
    json_data: dict[str, Any] = {"rejection_reason_id": rejection_reason_id}
    if notes is not None:
        json_data["notes"] = notes
    if rejection_email is not None:
        email = dict(rejection_email)
        if "email_from_user_id" not in email and str(client.user_id or "").isdigit():
            email["email_from_user_id"] = int(str(client.user_id))
        json_data["rejection_email"] = email
    result = await client.harvest_post(
        f"/applications/{application_id}/reject", json_data=json_data
    )
    return _done(result, application_id=application_id, status="rejected")


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
    result = await client.harvest_post(f"/applications/{application_id}/unreject")
    return _done(result, application_id=application_id, status="active")


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
    → match by name. Looks up the application's rejection details record and
    updates its reason.
    """
    details = await client.harvest_get(
        "/rejection_details", params={"application_ids": [application_id]}
    )
    if client._is_error(details):
        return details
    items = details.get("items") or []
    if not items:
        return {
            "error": "No rejection details found — this application doesn't appear to be "
            "rejected. Use reject_application to reject it.",
            "status_code": 404,
            "application_id": application_id,
        }
    detail_id = items[0]["id"]
    return await client.harvest_patch(
        f"/rejection_details/{detail_id}",
        json_data={"rejection_reason_id": rejection_reason_id},
    )


async def hire_application(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
    start_date: Annotated[
        str | None,
        Field(description="Hire start date: 'YYYY-MM-DD' or an ISO 8601 date-time"),
    ] = None,
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
        json_data["start_date"] = normalize_datetime(start_date)  # v3 wants a date-time
    if opening_id is not None:
        json_data["opening_id"] = opening_id
    if close_reason_id is not None:
        json_data["close_reason_id"] = close_reason_id
    result = await client.harvest_post(
        f"/applications/{application_id}/hire", json_data=json_data
    )
    return _done(result, application_id=application_id, status="hired")


async def convert_prospect(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Prospect application ID to convert")],
    job_id: Annotated[
        int, Field(description="Job ID to apply the prospect to — get from list_jobs")
    ],
    initial_stage_id: Annotated[
        int | None,
        Field(
            description="Starting interview stage on that job (list_job_stages_for_job) — "
            "defaults to the first stage"
        ),
    ] = None,
) -> dict[str, Any]:
    """Convert a sourced prospect into an active candidate on a job. Write operation.

    Users say "move this prospect into the Backend pipeline." The prospect's
    application_id comes from their prospect record (get_candidate → applications
    array, where prospect is true). Target job_id from list_jobs → match by name.
    """
    json_data: dict[str, Any] = {"job_id": job_id}
    if initial_stage_id is not None:
        json_data["to_job_interview_stage_id"] = initial_stage_id
    return await client.harvest_post(
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
            description="Type: 'resume', 'cover_letter', 'take_home_test', 'offer_letter', "
            "'other', ... ('admin_only' = 'other' with admin-only visibility)"
        ),
    ],
    content: Annotated[
        str | None, Field(description="Base64-encoded file content — provide this OR url, not both")
    ] = None,
    url: Annotated[
        str | None,
        Field(description="Public URL to fetch the file from — provide this OR content, not both"),
    ] = None,
    visibility: Annotated[
        str | None,
        Field(description="Who can see it: 'public', 'private', or 'admin_only'"),
    ] = None,
) -> dict[str, Any]:
    """Attach a file to a specific application. Write operation.

    To find the application_id: search_candidates_by_name → get_candidate →
    match the application to the job. The file type is inferred from the
    filename extension. add_attachment does the same when you only know the
    candidate.
    """
    body = _attachment_body(application_id, filename, type, content, url, visibility)
    if client._is_error(body):
        return body
    return await client.harvest_post("/attachments", json_data=body)
