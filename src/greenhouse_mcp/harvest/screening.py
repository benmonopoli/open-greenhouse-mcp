"""Harvest API — Composite screening tools.

High-level tools that assemble analysis-ready candidate screening packages
by combining multiple API calls into a single operation. Harvest v3 doesn't
embed jobs, sources, attachments or a candidate's applications, so they are
fetched in parallel and resolved by id.
"""

from __future__ import annotations

import asyncio
import html as html_module
import re
from datetime import datetime
from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient, add_date_filter
from greenhouse_mcp.harvest.workflows import (
    _person_name,
    _resolve_candidate_names,
    _resolve_names,
    _simple_status,
    _to_datetime,
)
from greenhouse_mcp.location import detect_candidate_location as _detect_candidate_location
from greenhouse_mcp.resume_parser import extract_resume_text as _extract_resume_text

# ─── Private helpers ──────────────────────────────────────────────────

_TAG_RE = re.compile(r"<[^>]+>")
_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_LI_RE = re.compile(r"<li[^>]*>", re.IGNORECASE)
_HEADING_RE = re.compile(r"<h[1-6][^>]*>", re.IGNORECASE)
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")


def _strip_html(text: str | None) -> str:
    """Strip HTML tags, converting structural elements to plain-text equivalents.

    - ``<br>`` → newline
    - ``<li>`` → ``\\n- ``
    - ``<h1>``–``<h6>`` → ``\\n\\n``
    - HTML entities (``&amp;``, etc.) are decoded
    - 3+ consecutive newlines are collapsed to 2

    Returns ``""`` for None or empty input.
    """
    if not text:
        return ""

    result = _BR_RE.sub("\n", text)
    result = _HEADING_RE.sub("\n\n", result)
    result = _LI_RE.sub("\n- ", result)
    result = _TAG_RE.sub("", result)
    result = html_module.unescape(result)
    result = _MULTI_NEWLINE_RE.sub("\n\n", result)
    return result.strip()


def _format_date(iso_str: str | None) -> str:
    """Convert an ISO 8601 date string to human-readable format (e.g. "April 15, 2026").

    Returns ``"Unknown"`` for None, or the raw string for unparseable input.
    """
    if iso_str is None:
        return "Unknown"

    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(iso_str, fmt)
            return dt.strftime("%B %d, %Y").replace(" 0", " ")
        except ValueError:
            continue

    # Handle timezone offsets like +05:00 that Python < 3.7 strptime can't parse
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%B %d, %Y").replace(" 0", " ")
    except (ValueError, AttributeError):
        pass

    return iso_str


def _extract_screening_answers(application: dict[str, Any]) -> list[dict[str, str]]:
    """Extract question/answer pairs from an application's answers list.

    Skips entries with empty questions. Uses ``"(no answer)"`` for null answers.
    """
    results: list[dict[str, str]] = []
    for entry in application.get("answers") or []:
        question = str(entry.get("question") or "")
        if not question:
            continue
        answer = entry.get("answer")
        results.append(
            {
                "question": question,
                "answer": str(answer) if answer is not None else "(no answer)",
            }
        )
    return results


def _build_application_history(
    applications: list[dict[str, Any]],
    job_names: dict[int, str] | None = None,
    rejection_reasons: dict[int, str] | None = None,
) -> dict[str, Any]:
    """Build a summary of a candidate's application history from v3 applications.

    Counts applications by status (v3 ``in_process`` counts as active), flags
    ``is_repeat_rejected`` when there are 3+ rejections and 0 hires, and includes
    per-application details with job and rejection-reason names resolved from
    the lookup maps.
    """
    job_names = job_names or {}
    rejection_reasons = rejection_reasons or {}

    rejected = 0
    hired = 0
    active = 0
    prior: list[dict[str, Any]] = []

    for app in sorted(applications, key=lambda a: a.get("created_at") or "", reverse=True):
        status = _simple_status(app.get("status"))
        if status == "rejected":
            rejected += 1
        elif status == "hired":
            hired += 1
        elif status == "active":
            active += 1

        job_id = app.get("job_id")
        if job_id:
            job_name = job_names.get(job_id, "Unknown")
        else:
            job_name = "Prospect (no job)" if app.get("prospect") else "Unknown"

        reason_id = app.get("rejection_reason_id")
        prior.append(
            {
                "application_id": app.get("id"),
                "job": job_name,
                "applied": _format_date(app.get("created_at")),
                "status": status,
                "rejection_reason": rejection_reasons.get(reason_id) if reason_id else None,
                "current_stage": app.get("stage_name"),
            }
        )

    return {
        "total_applications": len(applications),
        "rejected": rejected,
        "hired": hired,
        "active": active,
        "is_repeat_rejected": rejected >= 3 and hired == 0,
        "prior_applications": prior,
    }


def _pick_job_post(posts: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Prefer a live external post, then any external post, then anything with content."""
    with_content = [p for p in posts if p.get("content")]
    live_external = [p for p in with_content if p.get("live") and not p.get("internal")]
    external = [p for p in with_content if not p.get("internal")]
    for group in (live_external, external, with_content):
        if group:
            return group[0]
    return None


def _pick_resume(
    attachments: list[dict[str, Any]],
    application_id: int | None = None,
) -> dict[str, Any] | None:
    """Most recent resume — from this application if it has one, else any application."""
    resumes = [a for a in attachments if a.get("type") == "resume" and a.get("url")]
    if not resumes:
        return None
    resumes.sort(key=lambda a: (a.get("created_at") or "", a.get("id") or 0))
    own = [a for a in resumes if application_id and a.get("application_id") == application_id]
    return (own or resumes)[-1]


async def _resume_text(client: GreenhouseClient, attachment: dict[str, Any]) -> str | None:
    """Download an attachment and return its extracted text (or None)."""
    download = await client.download_url(attachment.get("url", ""))
    if client._is_error(download):
        return None
    if "content_base64" in download:
        return _extract_resume_text(
            download["content_base64"],
            download.get("content_type", ""),
            attachment.get("filename", ""),
        ) or None
    content = download.get("content")
    return str(content) if content else None


def _contact_links(candidate: dict[str, Any]) -> dict[str, str] | None:
    all_links = (candidate.get("social_media_addresses") or []) + (
        candidate.get("website_addresses") or []
    )
    if not all_links:
        return None
    links: dict[str, str] = {}
    for link in all_links:
        url_val = link.get("value", "")
        lowered = url_val.lower()
        if "linkedin" in lowered:
            links["linkedin"] = url_val
        elif "github" in lowered:
            links["github"] = url_val
        elif "twitter" in lowered or "x.com" in lowered:
            links["twitter"] = url_val
        else:
            links[url_val] = url_val
    return links


def _tag_names(candidate: dict[str, Any]) -> list[str]:
    """v3 candidate tags are plain strings."""
    names: list[str] = []
    for tag in candidate.get("tags") or []:
        name = tag.get("name", "") if isinstance(tag, dict) else str(tag or "")
        if name:
            names.append(name)
    return names


# ─── Public tool function ────────────────────────────────────────────


async def screen_candidate(
    client: GreenhouseClient,
    *,
    application_id: Annotated[
        int,
        Field(
            description="Application ID — search_candidates_by_name → "
            "list_applications(candidate_id=...) → match the job"
        ),
    ],
) -> dict[str, Any]:
    """Full screening package for one candidate application. Read-only.

    Users say "screen Sarah for the Backend role" or "give me the full picture."
    To get application_id: search_candidates_by_name → list_applications
    (candidate_id=...) → match the application to the job name. Returns
    profile, resume text, location, screening answers, job description, and
    application history (with job names and rejection reasons) in one call.
    """
    application = await client.harvest_get_by_id("/applications", application_id)
    if client._is_error(application):
        return {"error": f"Failed to fetch application {application_id}", "detail": application}

    candidate_id: int = application["candidate_id"]
    job_id = application.get("job_id")
    source_id = application.get("source_id")

    async def _none() -> dict[str, Any]:
        return {"items": []}

    candidate, posts_resp, attachments_resp, history_resp, sources = await asyncio.gather(
        client.harvest_get_by_id("/candidates", candidate_id),
        client.harvest_get("/job_posts", params={"job_ids": [job_id], "per_page": 50})
        if job_id
        else _none(),
        client.harvest_get_ids(
            "/attachments", "candidate_ids", [candidate_id], params={"type": "resume"}
        ),
        client.harvest_get_ids("/applications", "candidate_ids", [candidate_id]),
        _resolve_names(client, "/sources", {source_id} if source_id else set()),
    )
    if client._is_error(candidate):
        return {"error": f"Failed to fetch candidate {candidate_id}", "detail": candidate}

    # Job description
    job_description = "(no job post found)"
    if not client._is_error(posts_resp):
        post = _pick_job_post(posts_resp.get("items", []))
        if post:
            job_description = _strip_html(post.get("content", ""))

    # Application history — the candidate's applications plus their job / reason names
    history_apps = [] if client._is_error(history_resp) else history_resp.get("items", [])
    if not any(a.get("id") == application.get("id") for a in history_apps):
        history_apps = [application, *history_apps]
    job_ids = {a["job_id"] for a in history_apps if a.get("job_id")}
    reason_ids = {a["rejection_reason_id"] for a in history_apps if a.get("rejection_reason_id")}
    job_names, reasons = await asyncio.gather(
        _resolve_names(client, "/jobs", job_ids),
        _resolve_names(client, "/rejection_reasons", reason_ids, {"include_defaults": True}),
    )
    application_history = _build_application_history(history_apps, job_names, reasons)

    # Resume
    resume_text = "(no resume text extracted)"
    resume_filename = ""
    has_resume = False
    attachments = [] if client._is_error(attachments_resp) else attachments_resp.get("items", [])
    resume_att = _pick_resume(attachments, application.get("id"))
    if resume_att:
        resume_filename = resume_att.get("filename", "")
        text = await _resume_text(client, resume_att)
        if text:
            resume_text = text
            has_resume = True

    screening_answers = _extract_screening_answers(application)
    location = _detect_candidate_location(
        application,
        candidate,
        answers=screening_answers,
        resume_text=resume_text if has_resume else "",
    )

    emails = candidate.get("email_addresses") or []
    phones = candidate.get("phone_numbers") or []

    return {
        "candidate": {
            "id": candidate.get("id"),
            "name": _person_name(candidate),
            "preferred_name": candidate.get("preferred_name"),
            "company": candidate.get("company") or "",
            "title": candidate.get("title") or "",
            "email": emails[0].get("value") if emails else None,
            "phone": phones[0].get("value") if phones else None,
            "links": _contact_links(candidate),
            "tags": _tag_names(candidate),
            "location": location,
        },
        "application": {
            "id": application.get("id"),
            "applied_at": _format_date(application.get("created_at")),
            "source": sources.get(source_id, "Unknown") if source_id else "Unknown",
            "current_stage": application.get("stage_name") or "Unknown",
            "job_interview_stage_id": application.get("job_interview_stage_id"),
            "status": _simple_status(application.get("status")),
            "last_activity_at": application.get("last_activity_at"),
        },
        "job": {
            "id": job_id,
            "name": job_names.get(job_id, "Unknown") if job_id else "Unknown",
            "description": job_description,
        },
        "screening_answers": screening_answers,
        "resume": {
            "text": resume_text,
            "filename": resume_filename,
            "has_resume": has_resume,
        },
        "application_history": application_history,
    }


# ─── Public tool function — daily digest ─────────────────────────────


async def fetch_new_applications(
    client: GreenhouseClient,
    *,
    since: Annotated[str, Field(description="ISO 8601 date — e.g. '2026-04-14' for yesterday")],
    job_id: Annotated[
        int | None, Field(description="Filter to one job — list_jobs → match by name")
    ] = None,
    status: Annotated[
        str, Field(description="Filter by status: 'active', 'rejected', or 'hired'")
    ] = "active",
    include_candidate_details: Annotated[
        bool, Field(description="Include candidate names (adds API calls)")
    ] = True,
) -> dict[str, Any]:
    """Applications since a date, grouped by job — the daily digest. Read-only.

    Users say "what new applications came in since yesterday?" Pass since as
    an ISO date (applications created on or after it). Optionally filter to
    one job with job_id (list_jobs → match by name). Returns applications
    grouped by job with candidate names, sources, stages, and screening answers.
    """
    params: dict[str, Any] = {"per_page": 500, "status": status}
    add_date_filter(params, "created_at", gte=_to_datetime(since))
    if job_id is not None:
        params["job_ids"] = [job_id]

    apps_result = await client.harvest_get("/applications", params=params, paginate="all")
    if client._is_error(apps_result):
        return {"error": "Failed to fetch applications", "detail": apps_result}
    applications = apps_result.get("items", [])

    job_names, sources = await asyncio.gather(
        _resolve_names(client, "/jobs", {a["job_id"] for a in applications if a.get("job_id")}),
        _resolve_names(
            client, "/sources", {a["source_id"] for a in applications if a.get("source_id")}
        ),
    )

    jobs_map: dict[Any, dict[str, Any]] = {}
    for app in applications:
        app_job_id = app.get("job_id")
        if app_job_id not in jobs_map:
            jobs_map[app_job_id] = {
                "job_id": app_job_id,
                "job_name": job_names.get(app_job_id, "Unknown") if app_job_id else "Unknown",
                "candidates": [],
            }
        source_id = app.get("source_id")
        jobs_map[app_job_id]["candidates"].append(
            {
                "application_id": app.get("id"),
                "candidate_id": app.get("candidate_id"),
                "applied_at": _format_date(app.get("created_at")),
                "source": sources.get(source_id, "Unknown") if source_id else "Unknown",
                "current_stage": app.get("stage_name") or "Unknown",
                "location": app.get("location_address"),
                "screening_answers": _extract_screening_answers(app),
            }
        )

    if include_candidate_details and applications:
        names = await _resolve_candidate_names(
            client, {a["candidate_id"] for a in applications if a.get("candidate_id")}
        )
        for job_entry in jobs_map.values():
            for candidate in job_entry["candidates"]:
                cid = candidate.get("candidate_id")
                if cid is not None:
                    candidate["candidate_name"] = names.get(cid, str(cid))

    by_job = sorted(jobs_map.values(), key=lambda j: len(j["candidates"]), reverse=True)

    result: dict[str, Any] = {
        "since": since,
        "status_filter": status,
        "total_new_applications": len(applications),
        "jobs_with_new_applications": len(by_job),
        "by_job": by_job,
    }
    if apps_result.get("partial"):
        result["partial"] = True
        result["warnings"] = [apps_result.get("error")]
    return result
