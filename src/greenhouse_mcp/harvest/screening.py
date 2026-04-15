"""Harvest API — Composite screening tools.

High-level tools that assemble analysis-ready candidate screening packages
by combining multiple API calls into a single operation.
"""
from __future__ import annotations

import asyncio
import html as html_module
import re
from datetime import datetime
from typing import Any

from greenhouse_mcp.client import GreenhouseClient
from greenhouse_mcp.location import detect_candidate_location
from greenhouse_mcp.resume_parser import extract_resume_text

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


def _extract_screening_answers(application: dict) -> list[dict[str, str]]:
    """Extract question/answer pairs from an application's answers list.

    Skips entries with empty questions. Uses ``"(no answer)"`` for null answers.
    """
    results: list[dict[str, str]] = []
    for entry in application.get("answers", []):
        question = str(entry.get("question") or "")
        if not question:
            continue
        answer = entry.get("answer")
        results.append({
            "question": question,
            "answer": str(answer) if answer is not None else "(no answer)",
        })
    return results


def _build_application_history(candidate: dict) -> dict:
    """Build a summary of the candidate's application history.

    Counts applications by status, flags ``is_repeat_rejected`` when there are
    3+ rejections and 0 hires, and includes per-application details.
    """
    applications = candidate.get("applications", [])

    rejected = 0
    hired = 0
    active = 0
    prior: list[dict[str, Any]] = []

    for app in applications:
        status = app.get("status", "")
        if status == "rejected":
            rejected += 1
        elif status == "hired":
            hired += 1
        elif status == "active":
            active += 1

        jobs = app.get("jobs", [])
        job_name = jobs[0].get("name", "Unknown") if jobs else "Unknown"

        rejection_reason_obj = app.get("rejection_reason")
        rejection_reason = (
            rejection_reason_obj.get("name") if isinstance(rejection_reason_obj, dict) else None
        )

        current_stage_obj = app.get("current_stage")
        current_stage = (
            current_stage_obj.get("name") if isinstance(current_stage_obj, dict) else None
        )

        prior.append({
            "job": job_name,
            "applied": _format_date(app.get("applied_at")),
            "status": status,
            "rejection_reason": rejection_reason,
            "current_stage": current_stage,
        })

    return {
        "total_applications": len(applications),
        "rejected": rejected,
        "hired": hired,
        "active": active,
        "is_repeat_rejected": rejected >= 3 and hired == 0,
        "prior_applications": prior,
    }


# ─── Public tool function ────────────────────────────────────────────


async def screen_candidate(
    client: GreenhouseClient,
    *,
    application_id: int,
) -> dict[str, Any]:
    """Assemble a complete screening package for one candidate application.

    Fetches the application, candidate profile, job description, resume text,
    screening answers, location, and application history — everything an agent
    needs to evaluate a candidate in a single call. Replaces 4-5 separate
    tool calls (get_application, get_candidate, list_job_posts_for_job,
    download_attachment, read_candidate_resume).

    Returns a structured dict with sections: candidate (profile + contact +
    location), application (dates, source, stage), job (name + plain-text
    description), screening_answers, resume (extracted text), and
    application_history (prior applications with repeat-rejection flag).
    """
    # Step a: Fetch application
    application = await client.harvest_get_one(f"/applications/{application_id}")
    if "error" in application and "status_code" in application:
        return {"error": f"Failed to fetch application {application_id}", "detail": application}

    # Step b: Extract IDs
    candidate_id = application.get("candidate_id")
    jobs = application.get("jobs", [])
    job_id = jobs[0].get("id") if jobs else None
    job_name = jobs[0].get("name", "Unknown") if jobs else "Unknown"

    # Step c: Parallel fetch — candidate + job posts
    coros: list[Any] = [client.harvest_get_one(f"/candidates/{candidate_id}")]
    if job_id:
        coros.append(client.harvest_get(f"/jobs/{job_id}/job_posts", params={"per_page": 1}))

    results = await asyncio.gather(*coros)
    candidate = results[0]
    job_posts_resp = results[1] if job_id else {"items": []}

    if "error" in candidate and "status_code" in candidate:
        return {"error": f"Failed to fetch candidate {candidate_id}", "detail": candidate}

    # Step d: Extract job description
    if "error" in job_posts_resp and "status_code" in job_posts_resp:
        job_description = "(no job post found)"
    else:
        posts = job_posts_resp.get("items", [])
        if posts:
            job_description = _strip_html(posts[0].get("content", ""))
        else:
            job_description = "(no job post found)"

    # Step e: Download resume
    resume_text = "(no resume text extracted)"
    resume_filename = ""
    has_resume = False

    attachments = candidate.get("attachments", [])
    resume_attachments = [a for a in attachments if a.get("type") == "resume"]
    if resume_attachments:
        resume_att = resume_attachments[-1]  # Most recent
        resume_filename = resume_att.get("filename", "")
        url = resume_att.get("url", "")
        if url:
            download = await client.download_url(url)
            if not ("error" in download and "status_code" in download):
                if "content_base64" in download:
                    extracted = extract_resume_text(
                        download["content_base64"],
                        download.get("content_type", ""),
                        resume_filename,
                    )
                    if extracted:
                        resume_text = extracted
                        has_resume = True
                elif "content" in download:
                    resume_text = download["content"]
                    has_resume = True

    # Step f: Extract screening answers
    screening_answers = _extract_screening_answers(application)

    # Step g: Detect location
    location = detect_candidate_location(
        application,
        candidate,
        answers=screening_answers,
        resume_text=resume_text if has_resume else "",
    )

    # Step h: Build application history
    application_history = _build_application_history(candidate)

    # Step i: Assemble contact info
    emails = candidate.get("email_addresses", [])
    primary_email = emails[0].get("value") if emails else None

    phones = candidate.get("phone_numbers", [])
    primary_phone = phones[0].get("value") if phones else None

    social_links = candidate.get("social_media_addresses", [])
    website_links = candidate.get("website_addresses", [])
    links: dict[str, str] | None = None
    all_links = social_links + website_links
    if all_links:
        links = {}
        for link in all_links:
            url_val = link.get("value", "")
            if "linkedin" in url_val.lower():
                links["linkedin"] = url_val
            elif "github" in url_val.lower():
                links["github"] = url_val
            elif "twitter" in url_val.lower() or "x.com" in url_val.lower():
                links["twitter"] = url_val
            else:
                links[url_val] = url_val

    tags = [t.get("name", "") for t in candidate.get("tags", []) if t.get("name")]

    # Step j: Return structured package
    first_name = candidate.get("first_name", "")
    last_name = candidate.get("last_name", "")
    name = f"{first_name} {last_name}".strip()

    return {
        "candidate": {
            "id": candidate.get("id"),
            "name": name,
            "company": candidate.get("company", ""),
            "title": candidate.get("title", ""),
            "email": primary_email,
            "phone": primary_phone,
            "links": links,
            "tags": tags,
            "location": location,
        },
        "application": {
            "id": application.get("id"),
            "applied_at": _format_date(application.get("applied_at")),
            "source": (application.get("source") or {}).get("public_name", "Unknown"),
            "current_stage": (application.get("current_stage") or {}).get("name", "Unknown"),
            "status": application.get("status", ""),
        },
        "job": {
            "id": job_id,
            "name": job_name,
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


# ─── Batch name resolution ──────────────────────────────────────────


async def _resolve_candidate_names(
    client: GreenhouseClient,
    candidate_ids: set[int],
) -> dict[int, str]:
    """Batch-fetch candidate names by ID. Returns {id: "First Last"}.

    Greenhouse limits candidate_ids to 50 per request, so we chunk accordingly.
    """
    if not candidate_ids:
        return {}

    names: dict[int, str] = {}
    id_list = list(candidate_ids)

    for i in range(0, len(id_list), 50):
        chunk = id_list[i : i + 50]
        ids_param = ",".join(str(cid) for cid in chunk)
        result = await client.harvest_get(
            "/candidates",
            params={"candidate_ids": ids_param, "per_page": 50},
            paginate="single",
        )
        if "error" in result and "status_code" in result:
            break
        for c in result.get("items", []):
            cid = c.get("id")
            first = c.get("first_name", "")
            last = c.get("last_name", "")
            names[cid] = f"{first} {last}".strip()

        # Rate-limit delay between chunks
        if i + 50 < len(id_list):
            await asyncio.sleep(0.25)

    return names


# ─── Public tool function — daily digest ─────────────────────────────


async def fetch_new_applications(
    client: GreenhouseClient,
    *,
    since: str,
    job_id: int | None = None,
    status: str = "active",
    include_candidate_details: bool = True,
) -> dict:
    """Fetch applications created since a given date, grouped by job.

    This is the "what's new since yesterday" query — use it for daily digest
    workflows where you need a quick overview of incoming applications. Pass
    a ``job_id`` to filter to a single job, or omit it for all jobs.

    For full screening details on a specific candidate (resume, history,
    location), use ``screen_candidate`` with the application ID from the
    results.

    Returns a structured dict with applications grouped by job, sorted by
    candidate count descending. Each candidate entry includes applied date,
    source, current stage, and screening answers.
    """
    # Step a: Build params
    params: dict[str, Any] = {
        "per_page": 500,
        "created_after": since,
        "status": status,
    }
    if job_id is not None:
        params["job_id"] = job_id

    # Step b: Fetch all matching applications
    apps_result = await client.harvest_get(
        "/applications", params=params, paginate="all"
    )
    if "error" in apps_result and "status_code" in apps_result:
        return {"error": "Failed to fetch applications", "detail": apps_result}

    applications = apps_result.get("items", [])

    # Step c: Group by job
    jobs_map: dict[str, dict[str, Any]] = {}
    for app in applications:
        jobs_list = app.get("jobs", [])
        app_job_name = jobs_list[0].get("name", "Unknown") if jobs_list else "Unknown"
        app_job_id = jobs_list[0].get("id") if jobs_list else None

        if app_job_name not in jobs_map:
            jobs_map[app_job_name] = {
                "job_id": app_job_id,
                "job_name": app_job_name,
                "candidates": [],
            }

        # Step d: Build candidate entry
        entry: dict[str, Any] = {
            "application_id": app.get("id"),
            "candidate_id": app.get("candidate_id"),
            "applied_at": _format_date(app.get("applied_at")),
            "source": (app.get("source") or {}).get("public_name", "Unknown"),
            "current_stage": (app.get("current_stage") or {}).get("name", "Unknown"),
            "screening_answers": _extract_screening_answers(app),
        }
        jobs_map[app_job_name]["candidates"].append(entry)

    # Step e: Resolve candidate names if requested
    if include_candidate_details and applications:
        cand_ids: set[int] = {
            app.get("candidate_id")
            for app in applications
            if app.get("candidate_id")
        }
        names = await _resolve_candidate_names(client, cand_ids)
        for job_entry in jobs_map.values():
            for candidate in job_entry["candidates"]:
                cid = candidate.get("candidate_id")
                if cid is not None:
                    candidate["candidate_name"] = names.get(cid, str(cid))

    # Step f: Sort jobs by candidate count descending
    by_job = sorted(
        jobs_map.values(),
        key=lambda j: len(j["candidates"]),
        reverse=True,
    )

    # Step g: Return structured result
    return {
        "since": since,
        "status_filter": status,
        "total_new_applications": len(applications),
        "jobs_with_new_applications": len(by_job),
        "by_job": by_job,
    }
