"""Harvest API — Composite sourcing tools.

High-level tools that search the candidate database using structured fields
and batch-fetch resume text for deeper skill-based filtering.
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime
from typing import Any

from greenhouse_mcp.client import GreenhouseClient
from greenhouse_mcp.resume_parser import extract_resume_text

# ─── Private helpers ──────────────────────────────────────────────────


def _calculate_experience_years(employments: list[dict]) -> float | None:
    """Calculate total years of work experience from employment records.

    Sums duration of each employment entry that has start_date. Uses end_date
    if present, otherwise assumes current (uses today's date). Returns None if
    no employments have dates.

    Note: overlapping employment periods are counted independently, so
    candidates with concurrent jobs may show inflated totals.
    """
    total_days = 0
    has_any = False
    today = date.today()

    for emp in employments:
        start_str = emp.get("start_date")
        if not start_str:
            continue
        try:
            start = datetime.strptime(start_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue

        end_str = emp.get("end_date")
        if end_str:
            try:
                end = datetime.strptime(end_str, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                end = today
        else:
            end = today

        delta = (end - start).days
        if delta > 0:
            total_days += delta
            has_any = True

    if not has_any:
        return None
    return round(total_days / 365.25, 1)


def _matches_keywords(text: str, keywords: list[str]) -> list[str]:
    """Case-insensitive substring match. Returns list of matched keywords."""
    if not text or not keywords:
        return []
    lower_text = text.lower()
    return [kw for kw in keywords if kw.lower() in lower_text]


def _build_candidate_profile(candidate: dict) -> dict[str, Any]:
    """Extract a structured profile from a raw Greenhouse candidate object.

    Returns a dict with id, name, title, company, email, tags,
    employments, educations, and experience_years.
    """
    first = candidate.get("first_name", "")
    last = candidate.get("last_name", "")
    name = f"{first} {last}".strip()

    emails = candidate.get("email_addresses", [])
    email = emails[0].get("value") if emails else None

    tags = [
        t.get("name", "")
        for t in candidate.get("tags", [])
        if t.get("name")
    ]

    employments = []
    for emp in candidate.get("employments", []):
        employments.append({
            "company": emp.get("company_name", ""),
            "title": emp.get("title", ""),
            "start_date": emp.get("start_date"),
            "end_date": emp.get("end_date"),
        })

    educations = []
    for edu in candidate.get("educations", []):
        educations.append({
            "school": edu.get("school_name", ""),
            "degree": edu.get("degree", ""),
            "discipline": edu.get("discipline", ""),
        })

    experience_years = _calculate_experience_years(
        candidate.get("employments", [])
    )

    return {
        "id": candidate.get("id"),
        "name": name,
        "title": candidate.get("title", ""),
        "company": candidate.get("company", ""),
        "email": email,
        "tags": tags,
        "employments": employments,
        "educations": educations,
        "experience_years": experience_years,
    }


def _matches_filters(
    profile: dict,
    *,
    title_keywords: list[str] | None = None,
    company_keywords: list[str] | None = None,
    education_keywords: list[str] | None = None,
    min_experience_years: int | None = None,
    tags: list[str] | None = None,
) -> dict | None:
    """Check if a candidate profile matches the given filters.

    ANY filter that is provided must match (AND logic between filter types).
    Within a filter type, any keyword matching is sufficient (OR logic).

    Returns a match dict with {score: int, reasons: list[str]} if matched,
    None if not.
    Score = count of filter types that matched.
    """
    score = 0
    reasons: list[str] = []
    has_any_filter = False

    # Title keywords — match against current title + employment titles
    if title_keywords:
        has_any_filter = True
        title_text = profile.get("title", "")
        for emp in profile.get("employments", []):
            title_text += " " + emp.get("title", "")
        matched = _matches_keywords(title_text, title_keywords)
        if matched:
            score += 1
            reasons.append(f"title: {', '.join(matched)}")
        else:
            return None

    # Company keywords — match against current company + employment companies
    if company_keywords:
        has_any_filter = True
        company_text = profile.get("company", "")
        for emp in profile.get("employments", []):
            company_text += " " + emp.get("company", "")
        matched = _matches_keywords(company_text, company_keywords)
        if matched:
            score += 1
            reasons.append(f"company: {', '.join(matched)}")
        else:
            return None

    # Education keywords — match against school, degree, discipline
    if education_keywords:
        has_any_filter = True
        edu_text = ""
        for edu in profile.get("educations", []):
            edu_text += " ".join([
                edu.get("school", ""),
                edu.get("degree", ""),
                edu.get("discipline", ""),
            ]) + " "
        matched = _matches_keywords(edu_text, education_keywords)
        if matched:
            score += 1
            reasons.append(f"education: {', '.join(matched)}")
        else:
            return None

    # Minimum experience years
    if min_experience_years is not None:
        has_any_filter = True
        exp = profile.get("experience_years")
        if exp is not None and exp >= min_experience_years:
            score += 1
            reasons.append(f"experience: {exp} years")
        else:
            return None

    # Tags — case-insensitive match
    if tags:
        has_any_filter = True
        candidate_tags_lower = [
            t.lower() for t in profile.get("tags", [])
        ]
        matched_tags = [
            t for t in tags if t.lower() in candidate_tags_lower
        ]
        if matched_tags:
            score += 1
            reasons.append(f"tags: {', '.join(matched_tags)}")
        else:
            return None

    # If no filters were provided, match everything with score 0
    if not has_any_filter:
        return {"score": 0, "reasons": ["no filters applied"]}

    return {"score": score, "reasons": reasons}


# ─── Public tool functions ────────────────────────────────────────────


async def search_pipeline_candidates(
    client: GreenhouseClient,
    *,
    job_ids: list[int],
    statuses: list[str] | None = None,
    title_keywords: list[str] | None = None,
    company_keywords: list[str] | None = None,
    education_keywords: list[str] | None = None,
    min_experience_years: int | None = None,
    tags: list[str] | None = None,
    max_results: int = 50,
) -> dict[str, Any]:
    """Search within specific job pipelines for candidates matching criteria.

    Searches existing job pipelines for candidates matching structured
    criteria like title, company, education, experience, and tags. Useful
    for resurfacing past applicants or finding candidates already in the
    system for a similar role.

    Returns matched candidate profiles with match reasons. For resume-level
    search (skills, technologies), use batch_read_resumes on the results.
    """
    # Step 1: Fetch applications for each job, collect unique candidate IDs
    all_candidate_ids: set[int] = set()
    status_set = {s.lower() for s in statuses} if statuses else None

    for job_id in job_ids:
        result = await client.harvest_get(
            "/applications",
            params={"per_page": 500, "job_id": job_id},
            paginate="all",
        )
        if "error" in result and "status_code" in result:
            await asyncio.sleep(0.25)
            continue
        for app in result.get("items", []):
            if status_set and app.get("status", "").lower() not in status_set:
                continue
            cid = app.get("candidate_id")
            if cid:
                all_candidate_ids.add(cid)
        await asyncio.sleep(0.25)

    if not all_candidate_ids:
        return {
            "matched_candidates": [],
            "total_scanned": 0,
            "total_matched": 0,
        }

    # Step 2: Batch-fetch candidates in chunks of 50
    matched: list[dict[str, Any]] = []
    id_list = sorted(all_candidate_ids)

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

        for candidate in result.get("items", []):
            profile = _build_candidate_profile(candidate)
            match = _matches_filters(
                profile,
                title_keywords=title_keywords,
                company_keywords=company_keywords,
                education_keywords=education_keywords,
                min_experience_years=min_experience_years,
                tags=tags,
            )
            if match is not None:
                matched.append({
                    **profile,
                    "match_score": match["score"],
                    "match_reasons": match["reasons"],
                })

        if i + 50 < len(id_list):
            await asyncio.sleep(0.25)

    # Sort by match_score descending, cap at max_results
    matched.sort(key=lambda m: m["match_score"], reverse=True)
    matched = matched[:max_results]

    return {
        "matched_candidates": matched,
        "total_scanned": len(all_candidate_ids),
        "total_matched": len(matched),
    }


async def scan_all_candidates(
    client: GreenhouseClient,
    *,
    title_keywords: list[str] | None = None,
    company_keywords: list[str] | None = None,
    education_keywords: list[str] | None = None,
    min_experience_years: int | None = None,
    tags: list[str] | None = None,
    updated_after: str | None = None,
    max_pages: int = 20,
    max_results: int = 50,
) -> dict[str, Any]:
    """Scan the entire candidate database for candidates matching criteria.

    Not pipeline-specific — searches everyone. Returns matched candidate
    profiles with match reasons. Use updated_after (ISO 8601 date string)
    to limit scope (recommended for large databases).

    For resume-level search (skills, technologies), use batch_read_resumes
    on the results.
    """
    matched: list[dict[str, Any]] = []
    total_scanned = 0
    pages_fetched = 0

    params: dict[str, Any] = {"per_page": 500}
    if updated_after:
        params["updated_after"] = updated_after

    for page_num in range(1, max_pages + 1):
        params["page"] = page_num
        result = await client.harvest_get(
            "/candidates",
            params=params,
            paginate="single",
        )
        if "error" in result and "status_code" in result:
            break

        items = result.get("items", [])
        if not items:
            break

        pages_fetched += 1
        total_scanned += len(items)

        for candidate in items:
            profile = _build_candidate_profile(candidate)
            match = _matches_filters(
                profile,
                title_keywords=title_keywords,
                company_keywords=company_keywords,
                education_keywords=education_keywords,
                min_experience_years=min_experience_years,
                tags=tags,
            )
            if match is not None:
                matched.append({
                    **profile,
                    "match_score": match["score"],
                    "match_reasons": match["reasons"],
                })

        # Stop early if we have enough results
        if len(matched) >= max_results:
            break

        # Only delay if there are more pages to fetch
        if result.get("has_next"):
            await asyncio.sleep(0.25)
        else:
            break

    # Sort by match_score descending, cap at max_results
    matched.sort(key=lambda m: m["match_score"], reverse=True)
    matched = matched[:max_results]

    return {
        "matched_candidates": matched,
        "total_scanned": total_scanned,
        "total_matched": len(matched),
        "pages_fetched": pages_fetched,
    }


async def batch_read_resumes(
    client: GreenhouseClient,
    *,
    candidate_ids: list[int],
    max_candidates: int = 25,
) -> dict[str, Any]:
    """Batch-fetch and extract resume text for multiple candidates.

    Use after narrowing candidates with search_pipeline_candidates or
    scan_all_candidates to check for skills, technologies, or other
    details only found in resume text.

    Returns extracted text per candidate, rate-limited to respect API
    limits.
    """
    capped_ids = candidate_ids[:max_candidates]
    results: list[dict[str, Any]] = []

    # Batch-fetch candidates in chunks of 50
    candidates_by_id: dict[int, dict] = {}
    for i in range(0, len(capped_ids), 50):
        chunk = capped_ids[i : i + 50]
        ids_param = ",".join(str(cid) for cid in chunk)
        resp = await client.harvest_get(
            "/candidates",
            params={"candidate_ids": ids_param, "per_page": 50},
            paginate="single",
        )
        if "error" in resp and "status_code" in resp:
            break
        for c in resp.get("items", []):
            cid = c.get("id")
            if cid is not None:
                candidates_by_id[cid] = c

        if i + 50 < len(capped_ids):
            await asyncio.sleep(0.25)

    # For each candidate, find and download most recent resume
    for cid in capped_ids:
        candidate = candidates_by_id.get(cid)
        if candidate is None:
            results.append({
                "candidate_id": cid,
                "candidate_name": str(cid),
                "resume_filename": None,
                "resume_text": None,
                "has_resume": False,
            })
            continue

        first = candidate.get("first_name", "")
        last = candidate.get("last_name", "")
        name = f"{first} {last}".strip()

        attachments = candidate.get("attachments", [])
        resume_atts = [
            a for a in attachments if a.get("type") == "resume"
        ]

        if not resume_atts:
            results.append({
                "candidate_id": cid,
                "candidate_name": name,
                "resume_filename": None,
                "resume_text": None,
                "has_resume": False,
            })
            continue

        # Most recent resume
        resume_att = resume_atts[-1]
        filename = resume_att.get("filename", "")
        url = resume_att.get("url", "")

        if not url:
            results.append({
                "candidate_id": cid,
                "candidate_name": name,
                "resume_filename": filename,
                "resume_text": None,
                "has_resume": False,
            })
            continue

        download = await client.download_url(url)
        await asyncio.sleep(0.25)

        if "error" in download and "status_code" in download:
            results.append({
                "candidate_id": cid,
                "candidate_name": name,
                "resume_filename": filename,
                "resume_text": None,
                "has_resume": False,
            })
            continue

        resume_text = None
        if "content_base64" in download:
            extracted = extract_resume_text(
                download["content_base64"],
                download.get("content_type", ""),
                filename,
            )
            if extracted:
                resume_text = extracted
        elif "content" in download:
            resume_text = download["content"]

        results.append({
            "candidate_id": cid,
            "candidate_name": name,
            "resume_filename": filename,
            "resume_text": resume_text,
            "has_resume": resume_text is not None,
        })

    return {
        "resumes": results,
        "total_requested": len(capped_ids),
        "total_with_resume": sum(
            1 for r in results if r["has_resume"]
        ),
    }
