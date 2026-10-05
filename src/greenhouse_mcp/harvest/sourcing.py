"""Harvest API — Composite sourcing tools.

High-level tools that search the candidate database using structured fields
and batch-fetch resume text for deeper skill-based filtering. Harvest v3 keeps
employments, educations and attachments out of the candidate record, so they
are fetched in batches of 50 candidate ids and attached where needed.
"""

from __future__ import annotations

import asyncio
import re
from datetime import date, datetime
from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient, add_date_filter
from greenhouse_mcp.harvest.workflows import _person_name, _resolve_names, _to_datetime
from greenhouse_mcp.resume_parser import extract_resume_text as _extract_resume_text

# ─── Private helpers ──────────────────────────────────────────────────


def _calculate_experience_years(employments: list[dict[str, Any]]) -> float | None:
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


def _matches_whole_word(text: str, keywords: list[str]) -> list[str]:
    """Word-boundary keyword match. Returns keywords found as whole words.

    Unlike _matches_keywords (substring), this requires the keyword to appear
    at word boundaries — "Java" matches "Java developer" but not "JavaScript".
    Used for exclude_keywords where false positives silently drop candidates.
    """
    if not text or not keywords:
        return []
    lower_text = text.lower()
    matched = []
    for kw in keywords:
        escaped = re.escape(kw.lower())
        # (?<!\w) = not preceded by word char, (?!\w) = not followed by word char
        if re.search(r"(?<!\w)" + escaped + r"(?!\w)", lower_text):
            matched.append(kw)
    return matched


def _extract_keyword_snippets(
    text: str,
    keywords: list[str],
    context_chars: int = 80,
) -> list[dict[str, str]]:
    """Find keywords in text and extract surrounding context snippets.

    Returns a list of {keyword, snippet} dicts. Each snippet is up to
    ``context_chars`` characters on each side of the keyword occurrence.
    Duplicate keywords are included only once (first occurrence).
    """
    if not text or not keywords:
        return []
    lower_text = text.lower()
    seen: set[str] = set()
    snippets: list[dict[str, str]] = []
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower in seen:
            continue
        idx = lower_text.find(kw_lower)
        if idx == -1:
            continue
        seen.add(kw_lower)
        start = max(0, idx - context_chars)
        end = min(len(text), idx + len(kw) + context_chars)
        snippet = text[start:end].strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        snippets.append({"keyword": kw, "snippet": snippet})
    return snippets


def _build_candidate_profile(candidate: dict[str, Any]) -> dict[str, Any]:
    """Extract a structured profile from a v3 candidate record.

    ``employments``/``educations`` are the lists attached by _enrich_candidates
    (absent keys are treated as empty). Tags are plain strings in v3.

    Returns a dict with id, name, title, company, email, tags,
    employments, educations, and experience_years.
    """
    name = _person_name(candidate)

    emails = candidate.get("email_addresses") or []
    email = emails[0].get("value") if emails else None

    raw_tags = candidate.get("tags") or []
    tags: list[str] = []
    for t in raw_tags:
        if isinstance(t, dict):
            tag_name = t.get("name", "")
            if tag_name:
                tags.append(tag_name)
        elif isinstance(t, str) and t:
            tags.append(t)

    employments = []
    for emp in candidate.get("employments") or []:
        employments.append(
            {
                "company": emp.get("company_name", ""),
                "title": emp.get("title", ""),
                "start_date": emp.get("start_date"),
                "end_date": emp.get("end_date"),
            }
        )

    educations = []
    for edu in candidate.get("educations") or []:
        educations.append(
            {
                "school": edu.get("school_name", ""),
                "degree": edu.get("degree", ""),
                "discipline": edu.get("discipline", ""),
            }
        )

    experience_years = _calculate_experience_years(candidate.get("employments") or [])

    return {
        "id": candidate.get("id"),
        "name": name,
        "title": candidate.get("title") or "",
        "company": candidate.get("company") or "",
        "email": email,
        "tags": tags,
        "employments": employments,
        "educations": educations,
        "experience_years": experience_years,
    }


def _matches_filters(
    profile: dict[str, Any],
    *,
    title_keywords: list[str] | None = None,
    company_keywords: list[str] | None = None,
    education_keywords: list[str] | None = None,
    min_experience_years: int | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any] | None:
    """Check if a candidate profile matches the given filters.

    Matching uses soft logic to handle sparse Greenhouse data: if a candidate
    HAS structured data and it matches, their score increases. If the data
    is missing/empty, the filter is skipped (not treated as a mismatch).
    If the data IS present and contradicts the filter, the candidate is
    excluded.

    This means candidates with rich profiles rank higher, while candidates
    with sparse profiles still appear (they need resume review). Use
    batch_read_resumes on the results for skill-level verification.

    Returns a match dict with {score: int, reasons: list[str]} if matched,
    None only if data is present and contradicts a filter.
    """
    score = 0
    reasons: list[str] = []
    has_any_filter = False

    # Title keywords — match against current title + employment titles
    if title_keywords:
        has_any_filter = True
        title_text = profile.get("title", "") or ""
        for emp in profile.get("employments", []):
            title_text += " " + (emp.get("title", "") or "")
        title_text = title_text.strip()
        if title_text:
            matched = _matches_keywords(title_text, title_keywords)
            if matched:
                score += 2  # Strong signal when title matches
                reasons.append(f"title: {', '.join(matched)}")
            else:
                return None  # Has title data but doesn't match
        # else: no title data — skip, don't reject

    # Company keywords — match against current company + employment companies
    if company_keywords:
        has_any_filter = True
        company_text = profile.get("company", "") or ""
        for emp in profile.get("employments", []):
            company_text += " " + (emp.get("company", "") or "")
        company_text = company_text.strip()
        if company_text:
            matched = _matches_keywords(company_text, company_keywords)
            if matched:
                score += 1
                reasons.append(f"company: {', '.join(matched)}")
            else:
                return None  # Has company data but doesn't match

    # Education keywords — match against school, degree, discipline
    if education_keywords:
        has_any_filter = True
        edu_text = ""
        for edu in profile.get("educations", []):
            edu_text += (
                " ".join(
                    [
                        edu.get("school", "") or "",
                        edu.get("degree", "") or "",
                        edu.get("discipline", "") or "",
                    ]
                )
                + " "
            )
        edu_text = edu_text.strip()
        if edu_text:
            matched = _matches_keywords(edu_text, education_keywords)
            if matched:
                score += 1
                reasons.append(f"education: {', '.join(matched)}")
            else:
                return None  # Has education data but doesn't match

    # Minimum experience years
    if min_experience_years is not None:
        has_any_filter = True
        exp = profile.get("experience_years")
        if exp is not None:
            if exp >= min_experience_years:
                score += 1
                reasons.append(f"experience: {exp} years")
            else:
                return None  # Has experience data but insufficient
        # else: no employment dates — skip, don't reject

    # Tags — case-insensitive match
    if tags:
        has_any_filter = True
        candidate_tags = profile.get("tags", [])
        if candidate_tags:
            candidate_tags_lower = {t.lower() for t in candidate_tags}
            matched_tags = [t for t in tags if t.lower() in candidate_tags_lower]
            if matched_tags:
                score += 1
                reasons.append(f"tags: {', '.join(matched_tags)}")
            else:
                return None  # Has tags but none match

    # If no filters were provided, match everything with score 0
    if not has_any_filter:
        return {"score": 0, "reasons": ["no filters applied"]}

    if not reasons:
        reasons.append("no structured data — needs resume review")

    return {"score": score, "reasons": reasons}


_MAX_NEAR_MISSES = 5


async def _collect_pipeline_candidate_ids(
    client: GreenhouseClient,
    job_ids: list[int],
    statuses: list[str] | None = None,
) -> set[int]:
    """Fetch applications on the given jobs and collect unique candidate IDs.

    Batched by job (50 job ids per request). Statuses ('active', 'rejected',
    'hired', 'converted') are applied as the v3 ``status`` filter.
    Shared by search_pipeline_candidates and scan_pipeline_resumes.
    """
    if not job_ids:
        return set()
    status_filters: list[str | None] = [None]
    if statuses:
        status_filters = [*sorted({s.lower().strip() for s in statuses})]
    candidate_ids: set[int] = set()
    for status in status_filters:
        params: dict[str, Any] = {"per_page": 500}
        if status:
            params["status"] = "active" if status == "in_process" else status
        result = await client.harvest_get_ids("/applications", "job_ids", job_ids, params=params)
        if client._is_error(result):
            continue
        for app in result.get("items", []):
            cid = app.get("candidate_id")
            if cid:
                candidate_ids.add(cid)
    return candidate_ids


async def _fetch_candidates(
    client: GreenhouseClient,
    candidate_ids: list[int],
    fields: list[str] | None = None,
) -> dict[int, dict[str, Any]]:
    """Batch-fetch candidate records by id (50 per request). Returns {id: candidate}."""
    if not candidate_ids:
        return {}
    params: dict[str, Any] = {"per_page": 100}
    if fields:
        params["fields"] = fields
    result = await client.harvest_get_ids("/candidates", "ids", candidate_ids, params=params)
    if client._is_error(result):
        return {}
    return {c["id"]: c for c in result.get("items", []) if c.get("id") is not None}


async def _latest_resumes(
    client: GreenhouseClient,
    candidate_ids: list[int],
) -> dict[int, dict[str, Any]]:
    """Most recent resume attachment per candidate (batched). Returns {candidate_id: att}."""
    if not candidate_ids:
        return {}
    result = await client.harvest_get_ids(
        "/attachments",
        "candidate_ids",
        candidate_ids,
        params={"type": "resume", "per_page": 500},
    )
    if client._is_error(result):
        return {}
    latest: dict[int, dict[str, Any]] = {}
    for att in result.get("items", []):
        cid = att.get("candidate_id")
        if cid is None or att.get("type") != "resume":
            continue
        key = (att.get("created_at") or "", att.get("id") or 0)
        current = latest.get(cid)
        if current is None or key >= (current.get("created_at") or "", current.get("id") or 0):
            latest[cid] = att
    return latest


async def _enrich_candidates(
    client: GreenhouseClient,
    candidates: list[dict[str, Any]],
    *,
    employments: bool = True,
    educations: bool = True,
) -> None:
    """Attach ``employments`` and ``educations`` lists to v3 candidate records in place.

    v3 candidates don't embed them; they come from ``/candidate_employments`` and
    ``/candidate_educations`` (batched by candidate id). Education school, degree
    and discipline are custom field options, resolved to names in one more batch.
    Candidates that already have the key are left alone.
    """
    if employments:
        todo = [c for c in candidates if "employments" not in c and c.get("id") is not None]
        if todo:
            result = await client.harvest_get_ids(
                "/candidate_employments",
                "candidate_ids",
                [c["id"] for c in todo],
                params={"per_page": 500},
            )
            rows = [] if client._is_error(result) else result.get("items", [])
            by_cand: dict[Any, list[dict[str, Any]]] = {}
            for row in rows:
                by_cand.setdefault(row.get("candidate_id"), []).append(
                    {
                        "company_name": row.get("company_name") or "",
                        "title": row.get("title") or "",
                        "start_date": (row.get("start_date") or "")[:10] or None,
                        "end_date": (row.get("end_date") or "")[:10] or None,
                    }
                )
            for c in todo:
                emps = by_cand.get(c["id"], [])
                emps.sort(key=lambda e: e.get("start_date") or "", reverse=True)
                c["employments"] = emps

    if educations:
        todo = [c for c in candidates if "educations" not in c and c.get("id") is not None]
        if todo:
            result = await client.harvest_get_ids(
                "/candidate_educations",
                "candidate_ids",
                [c["id"] for c in todo],
                params={"per_page": 500},
            )
            rows = [] if client._is_error(result) else result.get("items", [])
            option_ids = {
                row.get(k)
                for row in rows
                for k in (
                    "school_name_custom_field_option_id",
                    "degree_custom_field_option_id",
                    "discipline_custom_field_option_id",
                )
                if row.get(k)
            }
            options = await _resolve_names(client, "/custom_field_options", option_ids)
            edu_by_cand: dict[Any, list[dict[str, Any]]] = {}
            for row in rows:
                edu_by_cand.setdefault(row.get("candidate_id"), []).append(
                    {
                        "school_name": options.get(row.get("school_name_custom_field_option_id"))
                        or "",
                        "degree": options.get(row.get("degree_custom_field_option_id")) or "",
                        "discipline": options.get(row.get("discipline_custom_field_option_id"))
                        or "",
                        "start_date": row.get("start_at"),
                        "end_date": row.get("end_at"),
                    }
                )
            for c in todo:
                c["educations"] = edu_by_cand.get(c["id"], [])


async def _match_candidates(
    client: GreenhouseClient,
    candidates: list[dict[str, Any]],
    *,
    title_keywords: list[str] | None,
    company_keywords: list[str] | None,
    education_keywords: list[str] | None,
    min_experience_years: int | None,
    tags: list[str] | None,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Enrich only what the filters need, then return (candidate, match) pairs."""
    await _enrich_candidates(
        client,
        candidates,
        employments=bool(title_keywords or company_keywords or min_experience_years is not None),
        educations=bool(education_keywords),
    )
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for candidate in candidates:
        match = _matches_filters(
            _build_candidate_profile(candidate),
            title_keywords=title_keywords,
            company_keywords=company_keywords,
            education_keywords=education_keywords,
            min_experience_years=min_experience_years,
            tags=tags,
        )
        if match is not None:
            pairs.append((candidate, match))
    return pairs


async def _finalise_matches(
    client: GreenhouseClient,
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
    max_results: int,
) -> list[dict[str, Any]]:
    """Sort by score, cap, fill in any profile data not fetched for filtering."""
    pairs.sort(key=lambda p: p[1]["score"], reverse=True)
    top = pairs[:max_results]
    await _enrich_candidates(client, [c for c, _ in top])
    return [
        {
            **_build_candidate_profile(candidate),
            "match_score": match["score"],
            "match_reasons": match["reasons"],
        }
        for candidate, match in top
    ]


# ─── Public tool functions ────────────────────────────────────────────


async def search_pipeline_candidates(
    client: GreenhouseClient,
    *,
    job_ids: Annotated[
        list[int], Field(description="Job IDs to search — list_jobs → get IDs for similar roles")
    ],
    statuses: Annotated[
        list[str] | None, Field(description="Filter by status: 'active', 'rejected', 'hired'")
    ] = None,
    title_keywords: Annotated[
        list[str] | None, Field(description="Job title keywords — e.g. ['VP', 'Director']")
    ] = None,
    company_keywords: Annotated[
        list[str] | None, Field(description="Company name keywords — e.g. ['Google', 'Stripe']")
    ] = None,
    education_keywords: Annotated[
        list[str] | None, Field(description="Education keywords — e.g. ['Stanford', 'MIT']")
    ] = None,
    min_experience_years: Annotated[
        int | None, Field(description="Minimum years of work experience")
    ] = None,
    tags: Annotated[list[str] | None, Field(description="Tag names to filter by")] = None,
    max_results: Annotated[int, Field(description="Maximum candidates to return")] = 50,
) -> dict[str, Any]:
    """Search pipelines by structured fields — title, company, education, tags. Read-only.

    Users say "find VP-level candidates in our pipelines" or "who do we have
    from Google?" Pass job_ids (list_jobs → get IDs for similar roles). Best
    when structured data (employment and education history) is populated. If
    few results, switch to scan_pipeline_resumes for resume-text search.
    Combine with batch_read_resumes to verify skill matches.
    """
    all_candidate_ids = await _collect_pipeline_candidate_ids(client, job_ids, statuses)
    if not all_candidate_ids:
        return {"matched_candidates": [], "total_scanned": 0, "total_matched": 0}

    candidates = list((await _fetch_candidates(client, sorted(all_candidate_ids))).values())
    pairs = await _match_candidates(
        client,
        candidates,
        title_keywords=title_keywords,
        company_keywords=company_keywords,
        education_keywords=education_keywords,
        min_experience_years=min_experience_years,
        tags=tags,
    )
    matched = await _finalise_matches(client, pairs, max_results)
    return {
        "matched_candidates": matched,
        "total_scanned": len(all_candidate_ids),
        "total_matched": len(matched),
    }


async def scan_all_candidates(
    client: GreenhouseClient,
    *,
    title_keywords: Annotated[
        list[str] | None, Field(description="Job title keywords — e.g. ['Engineer', 'Manager']")
    ] = None,
    company_keywords: Annotated[
        list[str] | None, Field(description="Company name keywords")
    ] = None,
    education_keywords: Annotated[list[str] | None, Field(description="Education keywords")] = None,
    min_experience_years: Annotated[
        int | None, Field(description="Minimum years of work experience")
    ] = None,
    tags: Annotated[list[str] | None, Field(description="Tag names to filter by")] = None,
    updated_after: Annotated[
        str | None, Field(description="ISO 8601 date — limit to recently updated candidates")
    ] = None,
    max_pages: Annotated[
        int, Field(description="Maximum pages to scan (500 candidates/page)")
    ] = 20,
    max_results: Annotated[int, Field(description="Maximum candidates to return")] = 50,
) -> dict[str, Any]:
    """Database-wide candidate search by structured fields. Read-only.

    Like search_pipeline_candidates but searches the full database, not just
    specific pipelines. Use when candidates might be in unexpected pipelines.
    Pass updated_after to limit scope on large databases (title, company and
    experience filters fetch employment history for every scanned page).
    Follow up with batch_read_resumes to validate matches.
    """
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    total_scanned = 0
    pages_fetched = 0

    params: dict[str, Any] = {"per_page": 500}
    if updated_after:
        add_date_filter(params, "updated_at", gt=_to_datetime(updated_after))

    for _ in range(max_pages):
        result = await client.harvest_get("/candidates", params=params, paginate="single")
        if client._is_error(result):
            break
        items = result.get("items", [])
        if not items:
            break
        pages_fetched += 1
        total_scanned += len(items)

        pairs.extend(
            await _match_candidates(
                client,
                items,
                title_keywords=title_keywords,
                company_keywords=company_keywords,
                education_keywords=education_keywords,
                min_experience_years=min_experience_years,
                tags=tags,
            )
        )
        if len(pairs) >= max_results:
            break
        if not result.get("has_next") or not result.get("next_cursor"):
            break
        params = {"cursor": result["next_cursor"]}

    matched = await _finalise_matches(client, pairs, max_results)
    return {
        "matched_candidates": matched,
        "total_scanned": total_scanned,
        "total_matched": len(matched),
        "pages_fetched": pages_fetched,
    }


async def _download_text(
    client: GreenhouseClient, attachment: dict[str, Any]
) -> str | None:
    download = await client.download_url(attachment.get("url", ""))
    if client._is_error(download):
        return None
    if "content_base64" in download:
        return (
            _extract_resume_text(
                download["content_base64"],
                download.get("content_type", ""),
                attachment.get("filename", ""),
            )
            or None
        )
    content = download.get("content")
    return str(content) if content else None


async def batch_read_resumes(
    client: GreenhouseClient,
    *,
    candidate_ids: Annotated[list[int], Field(description="Candidate IDs to fetch resumes for")],
    max_candidates: Annotated[int, Field(description="Maximum resumes to download")] = 25,
) -> dict[str, Any]:
    """Download and extract resume text for a list of candidates. Read-only.

    Use after narrowing candidates with other sourcing tools. Pass candidate_ids
    from search_pipeline_candidates or scan_all_candidates. Uses each
    candidate's most recent resume across all their applications. Full resume
    text reveals career trajectory, scope of work, and skills that structured
    data doesn't capture.
    """
    capped_ids = candidate_ids[:max_candidates]
    candidates_by_id = await _fetch_candidates(
        client, capped_ids, fields=["id", "first_name", "last_name"]
    )
    resumes = await _latest_resumes(client, capped_ids)

    results: list[dict[str, Any]] = []
    for cid in capped_ids:
        candidate = candidates_by_id.get(cid)
        name = _person_name(candidate) if candidate else str(cid)
        att = resumes.get(cid)
        entry: dict[str, Any] = {
            "candidate_id": cid,
            "candidate_name": name,
            "resume_filename": att.get("filename") if att else None,
            "resume_text": None,
            "has_resume": False,
        }
        if att and att.get("url"):
            text = await _download_text(client, att)
            await asyncio.sleep(0.25)
            entry["resume_text"] = text
            entry["has_resume"] = text is not None
        results.append(entry)

    return {
        "resumes": results,
        "total_requested": len(capped_ids),
        "total_with_resume": sum(1 for r in results if r["has_resume"]),
    }


async def scan_pipeline_resumes(
    client: GreenhouseClient,
    *,
    job_ids: Annotated[
        list[int], Field(description="Job IDs to search — list_jobs → get IDs for similar roles")
    ],
    keywords: Annotated[
        list[str] | None, Field(description="OR keywords — each hit boosts ranking")
    ] = None,
    required_keywords: Annotated[
        list[str] | None,
        Field(description="AND keywords — ALL must appear or candidate is skipped"),
    ] = None,
    exclude_keywords: Annotated[
        list[str] | None,
        Field(
            description="NOT keywords — any match disqualifies (word-boundary matching)"
        ),
    ] = None,
    statuses: Annotated[
        list[str] | None, Field(description="Filter by status: 'active', 'rejected', 'hired'")
    ] = None,
    max_resumes: Annotated[int, Field(description="Maximum resumes to scan")] = 25,
) -> dict[str, Any]:
    """Search resume text in pipelines for skills and qualifications. Read-only.

    Users say "find Rust engineers in our pipelines" or "search for distributed
    systems experience." The primary sourcing tool — ~90% of candidate data
    lives in resumes. Pass job_ids (list_jobs → get IDs for similar roles).
    Supports boolean search: keywords (OR), required_keywords (AND),
    exclude_keywords (NOT with word-boundary matching).
    """
    if not keywords and not required_keywords:
        raise ValueError("Provide at least one of keywords or required_keywords")

    all_candidate_ids = await _collect_pipeline_candidate_ids(client, job_ids, statuses)

    if not all_candidate_ids:
        return {
            "matched_candidates": [],
            "total_in_pipeline": 0,
            "resumes_scanned": 0,
            "total_matched": 0,
            "search_diagnostics": {
                "keyword_frequency": {},
                "excluded_count": 0,
                "excluded_by": {},
                "required_failed_count": 0,
                "near_misses": [],
            },
        }

    total_in_pipeline = len(all_candidate_ids)

    # Batch-fetch resumes and names for a candidate window (extra in case some lack resumes)
    ids_to_fetch = sorted(all_candidate_ids)[: max_resumes * 2]
    resumes = await _latest_resumes(client, ids_to_fetch)
    candidates_by_id = await _fetch_candidates(
        client, [c for c in ids_to_fetch if c in resumes], fields=["id", "first_name", "last_name"]
    )

    matched: list[dict[str, Any]] = []
    resumes_scanned = 0
    stats_excluded = 0
    stats_excluded_by: dict[str, int] = {}
    stats_required_failed = 0
    all_search_keywords = list(required_keywords or []) + list(keywords or [])
    stats_keyword_freq: dict[str, int] = {kw: 0 for kw in all_search_keywords}
    near_misses: list[dict[str, Any]] = []

    for cid in ids_to_fetch:
        if resumes_scanned >= max_resumes:
            break

        resume_att = resumes.get(cid)
        if not resume_att or not resume_att.get("url"):
            continue

        resume_text = await _download_text(client, resume_att)
        await asyncio.sleep(0.25)
        if not resume_text:
            continue

        resumes_scanned += 1
        candidate = candidates_by_id.get(cid) or {}
        name = _person_name(candidate) or str(cid)

        # Track keyword frequency across all scanned resumes (before filtering)
        for kw in _matches_whole_word(resume_text, all_search_keywords):
            stats_keyword_freq[kw] += 1

        # 1. Exclude gate — any excluded keyword found → skip
        if exclude_keywords:
            excluded_hits = _matches_whole_word(resume_text, exclude_keywords)
            if excluded_hits:
                stats_excluded += 1
                for ek in excluded_hits:
                    stats_excluded_by[ek] = stats_excluded_by.get(ek, 0) + 1
                continue

        # 2. Required gate — all required keywords must be present
        all_matched: list[str] = []
        if required_keywords:
            required_hits = _matches_whole_word(resume_text, required_keywords)
            if len(required_hits) < len(required_keywords):
                stats_required_failed += 1
                if required_hits and len(near_misses) < _MAX_NEAR_MISSES:
                    keyword_hits = _matches_keywords(resume_text, keywords) if keywords else []
                    near_misses.append(
                        {
                            "candidate_id": cid,
                            "candidate_name": name,
                            "matched_required": required_hits,
                            "missing_required": [
                                kw for kw in required_keywords if kw not in required_hits
                            ],
                            "matched_keywords": keyword_hits,
                        }
                    )
                continue
            all_matched.extend(required_hits)

        # 3. Preferred/general keywords — each match boosts score
        if keywords:
            all_matched.extend(_matches_keywords(resume_text, keywords))

        if not all_matched:
            continue

        matched.append(
            {
                "candidate_id": cid,
                "candidate_name": name,
                "matched_keywords": all_matched,
                "keyword_snippets": _extract_keyword_snippets(resume_text, all_matched),
                "resume_filename": resume_att.get("filename", ""),
            }
        )

    matched.sort(key=lambda m: len(m["matched_keywords"]), reverse=True)

    return {
        "matched_candidates": matched,
        "total_in_pipeline": total_in_pipeline,
        "resumes_scanned": resumes_scanned,
        "total_matched": len(matched),
        "search_diagnostics": {
            "keyword_frequency": stats_keyword_freq,
            "excluded_count": stats_excluded,
            "excluded_by": stats_excluded_by,
            "required_failed_count": stats_required_failed,
            "near_misses": near_misses,
        },
    }
