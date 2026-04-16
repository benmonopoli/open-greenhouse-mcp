"""Harvest API — Candidates tools (15 tools)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_candidates(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    page: Annotated[int, Field(description="Page number (starts at 1)")] = 1,
    email: Annotated[str | None, Field(description="Filter by exact email address")] = None,
    candidate_ids: Annotated[list[int] | None, Field(description="Filter to specific candidate IDs")] = None,
    created_after: Annotated[str | None, Field(description="ISO 8601 datetime — only candidates created after this")] = None,
    created_before: Annotated[str | None, Field(description="ISO 8601 datetime — only candidates created before this")] = None,
    updated_after: Annotated[str | None, Field(description="ISO 8601 datetime — only candidates updated after this")] = None,
    updated_before: Annotated[str | None, Field(description="ISO 8601 datetime — only candidates updated before this")] = None,
    paginate: Annotated[str, Field(description="'single' for one page, 'all' to auto-fetch every page")] = "single",
) -> dict[str, Any]:
    """List candidates with optional filters. Read-only.

    For finding a specific person, use search_candidates_by_name (by name) or
    search_candidates_by_email (by email) — faster and simpler. Use this tool
    for bulk operations: date-range queries, fetching by specific IDs, or
    paginating through the full database.
    """
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
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
) -> dict[str, Any]:
    """Get a candidate's full profile by ID. Read-only.

    Returns name, contact info, all applications (with job names and statuses),
    tags, custom fields, and attachments. This is the central lookup — most
    workflows route through here after resolving a name via
    search_candidates_by_name. For a screening package with resume and
    location, use screen_candidate.
    """
    return await client.harvest_get_one(f"/candidates/{candidate_id}")


async def create_candidate(
    client: GreenhouseClient,
    *,
    first_name: Annotated[str, Field(description="Candidate's first name")],
    last_name: Annotated[str, Field(description="Candidate's last name")],
    company: Annotated[str | None, Field(description="Current company name")] = None,
    title: Annotated[str | None, Field(description="Current job title")] = None,
    phone_numbers: Annotated[list[dict[str, Any]] | None, Field(description="Array of {value: '+1...', type: 'mobile'|'home'|'work'}")] = None,
    email_addresses: Annotated[list[dict[str, Any]] | None, Field(description="Array of {value: 'x@y.com', type: 'personal'|'work'}")] = None,
    addresses: Annotated[list[dict[str, Any]] | None, Field(description="Array of {value: '123 Main St', type: 'home'|'work'}")] = None,
    tags: Annotated[list[str] | None, Field(description="Tag name strings — tags are created on-the-fly if they don't exist")] = None,
    custom_fields: Annotated[list[dict[str, Any]] | None, Field(description="Array of {id: field_id, value: ...} — get field IDs from list_custom_fields")] = None,
) -> dict[str, Any]:
    """Create a new candidate record. Write operation.

    Users say "add a new candidate — Jane Doe at Acme Corp." Check for
    duplicates first with search_candidates_by_name or search_candidates_by_email.
    After creating, use create_application to apply them to a job. For sourced
    prospects, use add_prospect instead.
    """
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
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
    first_name: Annotated[str | None, Field(description="New first name")] = None,
    last_name: Annotated[str | None, Field(description="New last name")] = None,
    company: Annotated[str | None, Field(description="New company name")] = None,
    title: Annotated[str | None, Field(description="New job title")] = None,
    phone_numbers: Annotated[list[dict[str, Any]] | None, Field(description="Replaces all phone numbers: [{value: '+1...', type: 'mobile'|'home'|'work'}]")] = None,
    email_addresses: Annotated[list[dict[str, Any]] | None, Field(description="Replaces all emails: [{value: 'x@y.com', type: 'personal'|'work'}]")] = None,
    tags: Annotated[list[str] | None, Field(description="Replaces all tags — provide the full list, not just additions")] = None,
    custom_fields: Annotated[list[dict[str, Any]] | None, Field(description="Array of {id: field_id, value: ...} — get field IDs from list_custom_fields")] = None,
) -> dict[str, Any]:
    """Update a candidate's profile. Write operation — only changes fields you provide.

    Users say "update Sarah's title to Senior Engineer." To get the candidate_id:
    search_candidates_by_name → get_candidate. For custom field IDs:
    list_custom_fields → match by name.
    """
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
    primary_candidate_id: Annotated[int, Field(description="Candidate to keep — their record is preserved")],
    duplicate_candidate_id: Annotated[int, Field(description="Candidate to merge away — their record is removed after merge")],
) -> dict[str, Any]:
    """Merge a duplicate candidate into a primary record. Write operation — cannot be undone.

    Users say "these two Sarah Chens are the same person." Find both records with
    search_candidates_by_name. The duplicate's applications and data move to the
    primary. The duplicate record is removed.
    """
    json_data: dict[str, Any] = {
        "primary_candidate_id": primary_candidate_id,
        "duplicate_candidate_id": duplicate_candidate_id,
    }
    return await client.harvest_put("/candidates/merge", json_data=json_data)


async def anonymize_candidate(
    client: GreenhouseClient,
    *,
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
    fields: Annotated[list[str] | None, Field(description="Fields to anonymize, e.g. ['full_name','emails','phone_numbers','activity_items','educations','employments']. Omit for all.")] = None,
) -> dict[str, Any]:
    """Anonymize a candidate's personal data for GDPR/privacy compliance. Write operation.

    Removes specified fields (name, email, phone, etc.) while preserving the
    record and application history. Cannot be recovered. To get the candidate_id:
    search_candidates_by_name → get_candidate.
    """
    json_data: dict[str, Any] = {}
    if fields is not None:
        json_data["fields"] = fields
    return await client.harvest_put(
        f"/candidates/{candidate_id}/anonymize", json_data=json_data or None
    )


async def add_prospect(
    client: GreenhouseClient,
    *,
    first_name: Annotated[str, Field(description="Prospect's first name")],
    last_name: Annotated[str, Field(description="Prospect's last name")],
    company: Annotated[str | None, Field(description="Current company name")] = None,
    title: Annotated[str | None, Field(description="Current job title")] = None,
    phone_numbers: Annotated[list[dict[str, Any]] | None, Field(description="Array of {value: '+1...', type: 'mobile'|'home'|'work'}")] = None,
    email_addresses: Annotated[list[dict[str, Any]] | None, Field(description="Array of {value: 'x@y.com', type: 'personal'|'work'}")] = None,
    prospect_pool_id: Annotated[int | None, Field(description="Prospect pool to add to — get from list_prospect_pools")] = None,
    prospect_stage_id: Annotated[int | None, Field(description="Stage within the prospect pool")] = None,
    prospect_owner_id: Annotated[int | None, Field(description="User ID who owns this prospect — get from list_users")] = None,
) -> dict[str, Any]:
    """Create a sourced prospect in a prospect pool. Write operation.

    Users say "add this person as a prospect for the Engineering pool." Unlike
    create_candidate + create_application, this creates a prospect not yet in
    an active job pipeline. For pool/stage IDs: list_prospect_pools → match by
    name. To later convert to an active candidate, use convert_prospect.
    """
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
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
    school_id: Annotated[int | None, Field(description="School ID — get from list_schools")] = None,
    discipline_id: Annotated[int | None, Field(description="Academic discipline ID — get from list_disciplines")] = None,
    degree_id: Annotated[int | None, Field(description="Degree type ID — get from list_degrees")] = None,
    start_date: Annotated[str | None, Field(description="Start date as 'YYYY-MM-DD'")] = None,
    end_date: Annotated[str | None, Field(description="End date as 'YYYY-MM-DD'")] = None,
) -> dict[str, Any]:
    """Add an education record to a candidate. Write operation.

    To get candidate_id: search_candidates_by_name. For school_id: list_schools.
    For discipline_id: list_disciplines. For degree_id: list_degrees.
    """
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
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
    education_id: Annotated[int, Field(description="Education record ID from the candidate's profile")],
) -> dict[str, Any]:
    """Remove an education record from a candidate. Write operation — cannot be undone.

    To find education_id: get_candidate → the educations array.
    """
    return await client.harvest_delete(
        f"/candidates/{candidate_id}/educations/{education_id}"
    )


async def add_employment(
    client: GreenhouseClient,
    *,
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
    company_name: Annotated[str | None, Field(description="Employer company name")] = None,
    title: Annotated[str | None, Field(description="Job title at this employer")] = None,
    start_date: Annotated[str | None, Field(description="Start date as 'YYYY-MM-DD'")] = None,
    end_date: Annotated[str | None, Field(description="End date as 'YYYY-MM-DD' — omit for current role")] = None,
) -> dict[str, Any]:
    """Add a work history entry to a candidate. Write operation.

    To get candidate_id: search_candidates_by_name. Company name and title
    are free text — no ID lookup needed.
    """
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
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
    employment_id: Annotated[int, Field(description="Employment record ID from the candidate's profile")],
) -> dict[str, Any]:
    """Remove a work history entry from a candidate. Write operation — cannot be undone.

    To find employment_id: get_candidate → the employments array.
    """
    return await client.harvest_delete(
        f"/candidates/{candidate_id}/employments/{employment_id}"
    )


async def add_attachment(
    client: GreenhouseClient,
    *,
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
    filename: Annotated[str, Field(description="File name with extension, e.g. 'resume.pdf'")],
    type: Annotated[str, Field(description="Attachment type: 'resume', 'cover_letter', 'admin_only', or 'take_home_test'")],
    content: Annotated[str | None, Field(description="Base64-encoded file content — provide this OR url, not both")] = None,
    url: Annotated[str | None, Field(description="Public URL to fetch the file from — provide this OR content, not both")] = None,
    content_type: Annotated[str, Field(description="MIME type, e.g. 'application/pdf', 'application/msword'")] = "application/pdf",
) -> dict[str, Any]:
    """Attach a file (resume, cover letter, etc.) to a candidate record. Write operation.

    Shared across all the candidate's applications. To get candidate_id:
    search_candidates_by_name. To attach to a specific application only,
    use add_attachment_to_application instead.
    """
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
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
    body: Annotated[str, Field(description="Note text content (plain text or HTML)")],
    visibility: Annotated[str, Field(description="'private' (default, only visible to you) or 'public' (visible to all users)")] = "private",
) -> dict[str, Any]:
    """Add a text note to a candidate's activity feed. Write operation.

    Users say "add a note to Sarah's profile" or "log that I spoke with John."
    To get candidate_id: search_candidates_by_name.
    """
    json_data: dict[str, Any] = {"body": body, "visibility": visibility}
    return await client.harvest_post(
        f"/candidates/{candidate_id}/activity_feed/notes", json_data=json_data
    )


async def add_email_note_to_candidate(
    client: GreenhouseClient,
    *,
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
    to: Annotated[str, Field(description="Recipient email address")],
    from_: Annotated[str, Field(description="Sender email address")],
    subject: Annotated[str, Field(description="Email subject line")],
    body: Annotated[str, Field(description="Email body content")],
) -> dict[str, Any]:
    """Log an email on a candidate's activity feed. Write operation.

    Records an email exchange (to, from, subject, body) as an activity entry.
    This logs the email — it does not send one. To get candidate_id:
    search_candidates_by_name.
    """
    json_data: dict[str, Any] = {"to": to, "from": from_, "subject": subject, "body": body}
    return await client.harvest_post(
        f"/candidates/{candidate_id}/activity_feed/emails", json_data=json_data
    )
