"""Harvest API — Candidates tools (15 tools)."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient, add_date_filter
from greenhouse_mcp.harvest._custom_field_merge import merged_custom_fields
from greenhouse_mcp.harvest.applications import (
    _add_job_names,
    _attachment_body,
    _by_id,
    _invalid,
    _lookup,
    _v3_custom_fields,
    _with_warnings,
)

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _profile_fields(**fields: Any) -> dict[str, Any]:
    """Drop Nones and convert v1-style custom fields to v3."""
    out = {k: v for k, v in fields.items() if v is not None}
    if "custom_fields" in out:
        out["custom_fields"] = _v3_custom_fields(out["custom_fields"])
    return out


async def _hydrate_educations(
    client: GreenhouseClient, educations: list[dict[str, Any]], warnings: list[str]
) -> None:
    """Add school_name / degree / discipline names from custom field options, in place."""
    keys = (
        ("school_name", "school_name_custom_field_option_id"),
        ("degree", "degree_custom_field_option_id"),
        ("discipline", "discipline_custom_field_option_id"),
    )
    option_ids = {e.get(id_key) for e in educations for _, id_key in keys}
    options = _by_id(await _lookup(client, "/custom_field_options", option_ids, warnings))
    for edu in educations:
        for name_key, id_key in keys:
            option_id = edu.get(id_key)
            edu[name_key] = options.get(option_id, {}).get("name") if option_id else None


async def _check_owned(
    client: GreenhouseClient, endpoint: str, record_id: int, candidate_id: int
) -> dict[str, Any] | None:
    """Return an error dict unless ``record_id`` exists on ``endpoint`` for this candidate."""
    record = await client.harvest_get_by_id(endpoint, record_id)
    if client._is_error(record):
        return record
    if record.get("candidate_id") != candidate_id:
        return _invalid(
            f"Record {record_id} belongs to candidate {record.get('candidate_id')}, "
            f"not {candidate_id}. Nothing was removed."
        )
    return None


async def _pick_application(client: GreenhouseClient, candidate_id: int) -> Any:
    """The candidate's most recently active application (id), or an error dict."""
    apps = await client.harvest_get(
        "/applications", params={"candidate_ids": [candidate_id]}, paginate="all"
    )
    if client._is_error(apps):
        return apps
    items = apps.get("items") or []
    if not items:
        return _invalid(
            "This candidate has no applications; v3 stores attachments on applications. "
            "Use create_application first.",
            candidate_id=candidate_id,
        )
    items.sort(key=lambda a: a.get("last_activity_at") or a.get("created_at") or "", reverse=True)
    return items[0]["id"]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


async def list_candidates(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    cursor: Annotated[
        str | None,
        Field(description="Pass next_cursor from the previous response to get the next page"),
    ] = None,
    email: Annotated[str | None, Field(description="Filter by exact email address")] = None,
    candidate_ids: Annotated[
        list[int] | None, Field(description="Filter to specific candidate IDs (max 50)")
    ] = None,
    tag: Annotated[str | None, Field(description="Filter by exact candidate tag name")] = None,
    created_after: Annotated[
        str | None, Field(description="ISO 8601 datetime — only candidates created at/after this")
    ] = None,
    created_before: Annotated[
        str | None, Field(description="ISO 8601 datetime — only candidates created before this")
    ] = None,
    updated_after: Annotated[
        str | None, Field(description="ISO 8601 datetime — only candidates updated at/after this")
    ] = None,
    updated_before: Annotated[
        str | None, Field(description="ISO 8601 datetime — only candidates updated before this")
    ] = None,
    paginate: Annotated[
        str, Field(description="'single' for one page, 'all' to auto-fetch every page")
    ] = "single",
) -> dict[str, Any]:
    """List candidates with optional filters. Read-only.

    For finding a specific person, use search_candidates_by_name (by name) or
    search_candidates_by_email (by email) — faster and simpler. Use this tool
    for bulk operations: date-range queries, fetching by specific IDs, or
    paginating through the full database. Created and updated date filters
    can't be combined in one call. Candidates here are profile-only (no
    applications or attachments) — use get_candidate or
    list_applications(candidate_id=...) for those.
    """
    if (created_after or created_before) and (updated_after or updated_before):
        return _invalid(
            "Greenhouse v3 doesn't allow created and updated date filters together — "
            "use one or the other."
        )
    params: dict[str, Any] = {
        "per_page": per_page,
        "cursor": cursor,
        "email": email,
        "ids": candidate_ids,
        "tag": tag,
    }
    add_date_filter(params, "created_at", gte=created_after, lt=created_before)
    add_date_filter(params, "updated_at", gte=updated_after, lt=updated_before)
    return await client.harvest_get("/candidates", params=params, paginate=paginate)


async def get_candidate(
    client: GreenhouseClient,
    *,
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
    include_related: Annotated[
        bool,
        Field(
            description="Also fetch applications, attachments, educations and employments "
            "(default true; false returns the bare profile)"
        ),
    ] = True,
) -> dict[str, Any]:
    """Get a candidate's full profile by ID. Read-only.

    Returns name, contact info, tags, custom fields, plus (fetched alongside,
    since v3 no longer embeds them) applications (each with id, job_id,
    job_name, stage_name, job_interview_stage_id, status), attachments (with
    time-limited download URLs), educations (with school/degree/discipline
    names) and employments. This is the central lookup — most workflows route
    through here after resolving a name via search_candidates_by_name. For a
    screening package with resume and location, use screen_candidate.
    """
    candidate = await client.harvest_get_by_id("/candidates", candidate_id)
    if client._is_error(candidate) or not include_related:
        return candidate
    warnings: list[str] = []
    cid = [candidate_id]
    apps, attachments, educations, employments = await asyncio.gather(
        _lookup(client, "/applications", cid, warnings, filter_name="candidate_ids"),
        _lookup(client, "/attachments", cid, warnings, filter_name="candidate_ids"),
        _lookup(client, "/candidate_educations", cid, warnings, filter_name="candidate_ids"),
        _lookup(client, "/candidate_employments", cid, warnings, filter_name="candidate_ids"),
    )
    await asyncio.gather(
        _add_job_names(client, apps, warnings),
        _hydrate_educations(client, educations, warnings),
    )
    candidate["applications"] = apps
    candidate["attachments"] = attachments
    candidate["educations"] = educations
    candidate["employments"] = employments
    return _with_warnings(candidate, warnings)


async def create_candidate(
    client: GreenhouseClient,
    *,
    first_name: Annotated[str, Field(description="Candidate's first name")],
    last_name: Annotated[str, Field(description="Candidate's last name")],
    company: Annotated[str | None, Field(description="Current company name")] = None,
    title: Annotated[str | None, Field(description="Current job title")] = None,
    phone_numbers: Annotated[
        list[dict[str, Any]] | None,
        Field(description="Array of {value: '+1...', type: 'mobile'|'home'|'work'|'other'}"),
    ] = None,
    email_addresses: Annotated[
        list[dict[str, Any]] | None,
        Field(description="Array of {value: 'x@y.com', type: 'personal'|'work'|'other'}"),
    ] = None,
    addresses: Annotated[
        list[dict[str, Any]] | None,
        Field(description="Array of {value: '123 Main St', type: 'home'|'work'|'other'}"),
    ] = None,
    tags: Annotated[list[str] | None, Field(description="Candidate tag names to apply")] = None,
    custom_fields: Annotated[
        list[dict[str, Any]] | None,
        Field(
            description="Array of {custom_field_id (or name_key), value} — get field IDs "
            "from list_custom_fields"
        ),
    ] = None,
    job_id: Annotated[
        int | None,
        Field(description="Also apply them to this job (list_jobs) in the same call"),
    ] = None,
    source_id: Annotated[
        int | None, Field(description="Application source ID (list_sources) — needs job_id")
    ] = None,
    initial_stage_id: Annotated[
        int | None,
        Field(description="Starting interview stage (list_job_stages_for_job) — needs job_id"),
    ] = None,
    recruiter_id: Annotated[
        int | None, Field(description="Recruiter user ID (list_users) — needs job_id")
    ] = None,
    coordinator_id: Annotated[
        int | None, Field(description="Coordinator user ID (list_users) — needs job_id")
    ] = None,
    referrer_id: Annotated[
        int | None, Field(description="Referrer record ID — needs job_id")
    ] = None,
) -> dict[str, Any]:
    """Create a new candidate record, optionally applying them to a job. Write operation.

    Users say "add a new candidate — Jane Doe at Acme Corp for the Backend
    role." Check for duplicates first with search_candidates_by_name or
    search_candidates_by_email. Pass job_id (list_jobs) to create the
    application in the same call; the response then has both candidate and
    application. Without job_id, use create_application afterwards. For
    sourced prospects, use add_prospect instead.
    """
    json_data = _profile_fields(
        first_name=first_name,
        last_name=last_name,
        company=company,
        title=title,
        phone_numbers=phone_numbers,
        email_addresses=email_addresses,
        addresses=addresses,
        tags=tags,
        custom_fields=custom_fields,
    )
    application = _profile_fields(
        source_id=source_id,
        initial_stage_id=initial_stage_id,
        recruiter_id=recruiter_id,
        coordinator_id=coordinator_id,
        referrer_id=referrer_id,
    )
    if job_id is not None:
        json_data["application"] = {"job_id": job_id, **application}
    elif application:
        return _invalid(
            f"{', '.join(application)} only apply to an application — also pass job_id."
        )
    return await client.harvest_post("/candidates", json_data=json_data)


async def update_candidate(
    client: GreenhouseClient,
    *,
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
    first_name: Annotated[str | None, Field(description="New first name")] = None,
    last_name: Annotated[str | None, Field(description="New last name")] = None,
    company: Annotated[str | None, Field(description="New company name")] = None,
    title: Annotated[str | None, Field(description="New job title")] = None,
    phone_numbers: Annotated[
        list[dict[str, Any]] | None,
        Field(
            description="Replaces all phones: [{value: '+1...', type: 'mobile'|'home'|'work'}]"
        ),
    ] = None,
    email_addresses: Annotated[
        list[dict[str, Any]] | None,
        Field(description="Replaces all emails: [{value: 'x@y.com', type: 'personal'|'work'}]"),
    ] = None,
    tags: Annotated[
        list[str] | None,
        Field(description="Replaces all tags — provide the full list, not just additions"),
    ] = None,
    custom_fields: Annotated[
        list[dict[str, Any]] | None,
        Field(
            description="Array of {custom_field_id (or name_key), value} — only the fields "
            "to change; other custom field values are kept. Get field IDs from "
            "list_custom_fields"
        ),
    ] = None,
) -> dict[str, Any]:
    """Update a candidate's profile. Write operation — only changes fields you provide.

    Users say "update Sarah's title to Senior Engineer." To get the candidate_id:
    search_candidates_by_name → get_candidate. For custom field IDs:
    list_custom_fields → match by name. To add or remove a single tag without
    replacing the list, use add_tag_to_candidate / remove_tag_from_candidate.
    """
    json_data = _profile_fields(
        first_name=first_name,
        last_name=last_name,
        company=company,
        title=title,
        phone_numbers=phone_numbers,
        email_addresses=email_addresses,
        tags=tags,
    )
    if custom_fields is not None:
        # v3 replaces the whole collection: send current values plus this change.
        merged = await merged_custom_fields(client, "/candidates", candidate_id, custom_fields)
        if client._is_error(merged):
            return merged  # type: ignore[return-value]
        json_data["custom_fields"] = merged
    return await client.harvest_patch(f"/candidates/{candidate_id}", json_data=json_data)


async def delete_candidate(
    client: GreenhouseClient,
    *,
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID to delete")],
) -> dict[str, Any]:
    """Permanently delete a candidate and all their applications. Destructive — cannot be undone.

    To get the candidate_id: search_candidates_by_name → get_candidate.
    For GDPR compliance, consider anonymize_candidate instead — it preserves
    the record while removing personal data.
    """
    return await client.harvest_delete(f"/candidates/{candidate_id}")


async def merge_candidates(
    client: GreenhouseClient,
    *,
    primary_candidate_id: Annotated[
        int, Field(description="Candidate to keep — their record is preserved")
    ],
    duplicate_candidate_id: Annotated[
        int, Field(description="Candidate to merge away — their record is removed after merge")
    ],
) -> dict[str, Any]:
    """Merge a duplicate candidate into a primary record. Write operation — cannot be undone.

    Users say "these two Sarah Chens are the same person." Find both records with
    search_candidates_by_name. The duplicate's applications, attachments, notes
    and tags move to the primary, and the duplicate record is deleted. Returns
    the merged primary candidate.
    """
    return await client.harvest_post(
        f"/candidates/{primary_candidate_id}/merge",
        json_data={"secondary_candidate_id": duplicate_candidate_id},
    )


async def anonymize_candidate(
    client: GreenhouseClient,
    *,
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
    fields: Annotated[
        list[str],
        Field(
            description="Data groups to scrub (at least one), e.g. ['full_name', "
            "'email_addresses', 'phone_numbers', 'addresses', 'attachments', 'notes', "
            "'education', 'employment', 'scorecards_and_interviews', 'offers']"
        ),
    ],
) -> dict[str, Any]:
    """Anonymize a candidate's personal data for GDPR/privacy compliance. Write operation.

    Scrubs the listed data groups (name, emails, phones, attachments, notes,
    etc.) while preserving the record and hiring activity for reporting.
    Irreversible; large scopes complete asynchronously. Greenhouse requires an
    explicit list of fields — confirm with the user what to remove. To get the
    candidate_id: search_candidates_by_name → get_candidate.
    """
    if not fields:
        return _invalid("Provide at least one field to anonymize.")
    return await client.harvest_patch(
        f"/candidates/{candidate_id}/anonymize", json_data={"fields": fields}
    )


async def add_prospect(
    client: GreenhouseClient,
    *,
    first_name: Annotated[str, Field(description="Prospect's first name")],
    last_name: Annotated[str, Field(description="Prospect's last name")],
    company: Annotated[str | None, Field(description="Current company name")] = None,
    title: Annotated[str | None, Field(description="Current job title")] = None,
    phone_numbers: Annotated[
        list[dict[str, Any]] | None,
        Field(description="Array of {value: '+1...', type: 'mobile'|'home'|'work'}"),
    ] = None,
    email_addresses: Annotated[
        list[dict[str, Any]] | None,
        Field(description="Array of {value: 'x@y.com', type: 'personal'|'work'}"),
    ] = None,
    prospect_pool_id: Annotated[
        int | None, Field(description="Prospect pool to add to — get from list_prospect_pools")
    ] = None,
    prospect_stage_id: Annotated[
        int | None, Field(description="Stage within the prospect pool")
    ] = None,
    prospect_owner_id: Annotated[
        int | None, Field(description="User ID who owns this prospect — get from list_users")
    ] = None,
    job_ids: Annotated[
        list[int] | None,
        Field(description="Jobs this prospect is being considered for — from list_jobs"),
    ] = None,
) -> dict[str, Any]:
    """Create a sourced prospect in a prospect pool. Write operation.

    Users say "add this person as a prospect for the Engineering pool." Unlike
    create_candidate with a job_id, this creates a prospect not yet in an
    active job pipeline. For pool/stage IDs: list_prospect_pools → match by
    name. To later convert to an active candidate, use convert_prospect.
    """
    json_data = _profile_fields(
        first_name=first_name,
        last_name=last_name,
        company=company,
        title=title,
        phone_numbers=phone_numbers,
        email_addresses=email_addresses,
    )
    json_data["application"] = {
        "prospect": True,
        **_profile_fields(
            prospect_pool_id=prospect_pool_id,
            prospect_pool_stage_id=prospect_stage_id,
            prospect_owner_id=prospect_owner_id,
            job_ids=job_ids,
        ),
    }
    return await client.harvest_post("/candidates", json_data=json_data)


async def add_education(
    client: GreenhouseClient,
    *,
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
    school_id: Annotated[
        int | None, Field(description="School option ID — get from list_schools")
    ] = None,
    discipline_id: Annotated[
        int | None, Field(description="Discipline option ID — get from list_disciplines")
    ] = None,
    degree_id: Annotated[
        int | None, Field(description="Degree option ID — get from list_degrees")
    ] = None,
    start_date: Annotated[str | None, Field(description="Start date as 'YYYY-MM-DD'")] = None,
    end_date: Annotated[str | None, Field(description="End date as 'YYYY-MM-DD'")] = None,
) -> dict[str, Any]:
    """Add an education entry to a candidate. Write operation.

    To find candidate_id: search_candidates_by_name. For school_id:
    list_schools; degree_id: list_degrees; discipline_id: list_disciplines
    (match by name — these are custom field option IDs in Harvest v3).
    """
    json_data = _profile_fields(
        candidate_id=candidate_id,
        school_name_custom_field_option_id=school_id,
        degree_custom_field_option_id=degree_id,
        discipline_custom_field_option_id=discipline_id,
        start_date=start_date,
        end_date=end_date,
    )
    return await client.harvest_post("/candidate_educations", json_data=json_data)


async def remove_education(
    client: GreenhouseClient,
    *,
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
    education_id: Annotated[
        int, Field(description="Education record ID from the candidate's profile")
    ],
) -> dict[str, Any]:
    """Remove an education entry from a candidate. Write operation.

    To find candidate_id: search_candidates_by_name. For education_id:
    get_candidate → check the educations array. Checks the record belongs to
    this candidate before deleting it.
    """
    error = await _check_owned(client, "/candidate_educations", education_id, candidate_id)
    if error is not None:
        return error
    return await client.harvest_delete(f"/candidate_educations/{education_id}")


async def add_employment(
    client: GreenhouseClient,
    *,
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
    company_name: Annotated[str | None, Field(description="Employer company name")] = None,
    title: Annotated[str | None, Field(description="Job title at this employer")] = None,
    start_date: Annotated[str | None, Field(description="Start date as 'YYYY-MM-DD'")] = None,
    end_date: Annotated[
        str | None, Field(description="End date as 'YYYY-MM-DD' — omit for current role")
    ] = None,
) -> dict[str, Any]:
    """Add an employment entry to a candidate. Write operation.

    company_name, title and start_date are required by Greenhouse. To find
    candidate_id: search_candidates_by_name.
    """
    missing = [
        name
        for name, value in (
            ("company_name", company_name),
            ("title", title),
            ("start_date", start_date),
        )
        if not value
    ]
    if missing:
        return _invalid(f"Missing required field(s): {', '.join(missing)}.")
    json_data = _profile_fields(
        candidate_id=candidate_id,
        company_name=company_name,
        title=title,
        start_date=start_date,
        end_date=end_date,
    )
    return await client.harvest_post("/candidate_employments", json_data=json_data)


async def remove_employment(
    client: GreenhouseClient,
    *,
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
    employment_id: Annotated[
        int, Field(description="Employment record ID from the candidate's profile")
    ],
) -> dict[str, Any]:
    """Remove an employment entry from a candidate. Write operation.

    To find candidate_id: search_candidates_by_name. For employment_id:
    get_candidate → check the employments array. Checks the record belongs to
    this candidate before deleting it.
    """
    error = await _check_owned(client, "/candidate_employments", employment_id, candidate_id)
    if error is not None:
        return error
    return await client.harvest_delete(f"/candidate_employments/{employment_id}")


async def add_attachment(
    client: GreenhouseClient,
    *,
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
    filename: Annotated[str, Field(description="File name with extension, e.g. 'resume.pdf'")],
    type: Annotated[
        str,
        Field(
            description="Type: 'resume', 'cover_letter', 'take_home_test', 'other', ... "
            "('admin_only' = 'other' with admin-only visibility)"
        ),
    ],
    content: Annotated[
        str | None, Field(description="Base64-encoded file content — provide this OR url, not both")
    ] = None,
    url: Annotated[
        str | None,
        Field(description="Public URL to fetch the file from — provide this OR content, not both"),
    ] = None,
    application_id: Annotated[
        int | None,
        Field(
            description="Application to attach to — omit to use the candidate's most "
            "recently active application"
        ),
    ] = None,
    visibility: Annotated[
        str | None,
        Field(description="Who can see it: 'public', 'private', or 'admin_only'"),
    ] = None,
) -> dict[str, Any]:
    """Attach a file (resume, cover letter, etc.) to a candidate. Write operation.

    Harvest v3 stores every attachment on an application, so this attaches to
    application_id if given, otherwise to the candidate's most recently active
    application (the response's application_id shows which). To get
    candidate_id: search_candidates_by_name. To choose the application, see
    get_candidate's applications array, or use add_attachment_to_application.
    """
    if application_id is None:
        picked = await _pick_application(client, candidate_id)
        if client._is_error(picked):
            return picked  # type: ignore[no-any-return]
        application_id = int(picked)
    body = _attachment_body(application_id, filename, type, content, url, visibility)
    if client._is_error(body):
        return body
    return await client.harvest_post("/attachments", json_data=body)


async def add_note_to_candidate(
    client: GreenhouseClient,
    *,
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
    body: Annotated[str, Field(description="Note text content (plain text)")],
    visibility: Annotated[
        str,
        Field(
            description="'private' (default), 'public' (all users with access), or "
            "'admin_only'"
        ),
    ] = "private",
    application_id: Annotated[
        int | None,
        Field(description="Optionally anchor the note to one of the candidate's applications"),
    ] = None,
) -> dict[str, Any]:
    """Add a text note to a candidate's Notes tab / activity feed. Write operation.

    Users say "add a note to Sarah's profile" or "log that I spoke with John."
    The note is authored by the configured Greenhouse user. To get
    candidate_id: search_candidates_by_name.
    """
    json_data = _profile_fields(
        candidate_id=candidate_id,
        body=body,
        note_type="NOTE",
        visibility=visibility,
        application_id=application_id,
    )
    return await client.harvest_post("/notes", json_data=json_data)


async def add_email_note_to_candidate(
    client: GreenhouseClient,
    *,
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
    to: Annotated[str, Field(description="Recipient email address")],
    from_: Annotated[str, Field(description="Sender email address")],
    subject: Annotated[str, Field(description="Email subject line")],
    body: Annotated[str, Field(description="Email body content")],
    cc: Annotated[list[str] | None, Field(description="Cc email addresses")] = None,
    visibility: Annotated[
        str, Field(description="'public' (default), 'private', or 'admin_only'")
    ] = "public",
) -> dict[str, Any]:
    """Log an email on a candidate's activity feed. Write operation.

    Records an email exchange (to, from, cc, subject, body) as an activity
    entry. This logs the email — it does not send one. To get candidate_id:
    search_candidates_by_name.
    """
    json_data: dict[str, Any] = {
        "candidate_id": candidate_id,
        "note_type": "EMAIL",
        "subject": subject,
        "body": body,
        "email_to": [to],
        "email_from": [from_],
        "email_cc": cc or [],
        "visibility": visibility,
    }
    return await client.harvest_post("/notes", json_data=json_data)
