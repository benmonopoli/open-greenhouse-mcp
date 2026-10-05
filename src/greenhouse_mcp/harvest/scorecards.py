"""Harvest API — Scorecards tools (3 tools).

v3 splits a scorecard across several resources: attribute ratings
(``scorecard_candidate_attributes`` → ``job_candidate_attributes`` for names), question
answers (``scorecard_question_answers`` → ``scorecard_questions`` /
``scorecard_question_options``), and the interview via ``interview_kits`` →
``job_interviews``. These tools stitch them back together with batched lookups so each
scorecard reads like v1: interviewer, interview, overall recommendation, attributes and
question answers.
"""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient, add_date_filter
from greenhouse_mcp.harvest.jobs import _by_id, _lookup, _user_ref, _with_warnings

_SELECT_TYPES = ("single_select", "multi_select")


def _option_ids(value: Any) -> list[int]:
    values = value if isinstance(value, list) else [value]
    out: list[int] = []
    for v in values:
        if isinstance(v, bool):
            continue
        if isinstance(v, int):
            out.append(v)
        elif isinstance(v, str) and v.isdigit():
            out.append(int(v))
    return out


def _answer_text(
    answer: dict[str, Any], question: dict[str, Any], options: dict[int, dict[str, Any]]
) -> Any:
    kind = question.get("answer_type")
    value = answer.get("value")
    if kind == "yes_no":
        flag = answer.get("boolean_value")
        if flag is None and isinstance(value, bool):
            flag = value
        return None if flag is None else ("Yes" if flag else "No")
    if kind in _SELECT_TYPES:
        names = [options.get(i, {}).get("name") or str(i) for i in _option_ids(value)]
        return ", ".join(names) if names else None
    return answer.get("answer") if answer.get("answer") is not None else value


async def _hydrate_scorecards(
    client: GreenhouseClient, scorecards: list[dict[str, Any]], warnings: list[str]
) -> None:
    """Add interviewer, submitted_by, interview, attributes, ratings and questions in place."""
    if not scorecards:
        return
    sc_ids = {s.get("id") for s in scorecards}
    attrs, answers, users_list, kits = await asyncio.gather(
        _lookup(client, "/scorecard_candidate_attributes", sc_ids, warnings,
                filter_name="scorecard_ids"),
        _lookup(client, "/scorecard_question_answers", sc_ids, warnings,
                filter_name="scorecard_ids"),
        _lookup(
            client, "/users",
            {s.get("interviewer_id") for s in scorecards}
            | {s.get("submitter_id") for s in scorecards},
            warnings,
        ),
        _lookup(client, "/interview_kits", {s.get("interview_kit_id") for s in scorecards},
                warnings),
    )
    option_ids = {i for a in answers for i in _option_ids(a.get("value"))}
    job_attrs, questions, options, slots = await asyncio.gather(
        _lookup(client, "/job_candidate_attributes",
                {a.get("job_candidate_attribute_id") for a in attrs}, warnings),
        _lookup(client, "/scorecard_questions",
                {a.get("scorecard_question_id") for a in answers}, warnings),
        _lookup(client, "/scorecard_question_options", option_ids, warnings),
        _lookup(client, "/job_interviews", {k.get("job_interview_id") for k in kits}, warnings),
    )
    users, kit_map, slot_map = _by_id(users_list), _by_id(kits), _by_id(slots)
    attr_map, q_map, opt_map = _by_id(job_attrs), _by_id(questions), _by_id(options)

    attrs_by_sc: dict[int, list[dict[str, Any]]] = {}
    for a in attrs:
        meta = attr_map.get(a.get("job_candidate_attribute_id") or 0, {})
        attrs_by_sc.setdefault(a.get("scorecard_id") or 0, []).append({
            "id": a.get("job_candidate_attribute_id"),
            "name": meta.get("name"),
            "rating": a.get("candidate_attribute_rating") or a.get("value"),
            "note": a.get("note"),
            "_sort": meta.get("sort_order") or 0,
        })
    answers_by_sc: dict[int, list[dict[str, Any]]] = {}
    for ans in answers:
        q = q_map.get(ans.get("scorecard_question_id") or 0, {})
        answers_by_sc.setdefault(ans.get("scorecard_id") or 0, []).append({
            "id": ans.get("scorecard_question_id"),
            "question": q.get("question"),
            "answer_type": q.get("answer_type"),
            "answer": _answer_text(ans, q, opt_map),
            "_sort": q.get("sort_order") or 0,
        })

    for sc in scorecards:
        sid = sc.get("id") or 0
        kit = kit_map.get(sc.get("interview_kit_id") or 0, {})
        slot_id = kit.get("job_interview_id")
        slot_name = slot_map.get(slot_id or 0, {}).get("name")
        sc["interviewer"] = _user_ref(sc.get("interviewer_id"), users)
        sc["submitted_by"] = _user_ref(sc.get("submitter_id"), users)
        sc["interview"] = slot_name
        sc["interview_step"] = {"id": slot_id, "name": slot_name}
        sc["overall_recommendation"] = sc.get("candidate_rating")
        sc_attrs = sorted(attrs_by_sc.get(sid, []), key=lambda a: a.pop("_sort"))
        sc["attributes"] = sc_attrs
        ratings: dict[str, list[str]] = {}
        for a in sc_attrs:
            if a.get("rating"):
                ratings.setdefault(a["rating"], []).append(a.get("name") or str(a.get("id")))
        sc["ratings"] = ratings
        sc["questions"] = sorted(answers_by_sc.get(sid, []), key=lambda q: q.pop("_sort"))


async def list_scorecards(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    cursor: Annotated[
        str | None,
        Field(description="Pass next_cursor from the previous response to get the next page"),
    ] = None,
    created_after: Annotated[
        str | None, Field(description="ISO 8601 datetime — only scorecards created at/after this")
    ] = None,
    created_before: Annotated[
        str | None, Field(description="ISO 8601 datetime — only scorecards created before this")
    ] = None,
    status: Annotated[
        str | None, Field(description="'complete' for submitted scorecards, 'draft' for drafts")
    ] = None,
    include_details: Annotated[
        bool,
        Field(
            description="Resolve interviewer, interview, attribute ratings and question "
            "answers (extra calls; set false for faster bulk listing)"
        ),
    ] = True,
    paginate: Annotated[
        str, Field(description="'single' for one page, 'all' to auto-fetch every page")
    ] = "single",
) -> dict[str, Any]:
    """List interview scorecards across all applications. Read-only.

    Each scorecard has application_id, candidate_rating (also as
    overall_recommendation), notes, status, interviewed_at, submitted_at and,
    with include_details, interviewer/submitted_by {id, name, email},
    interview name, attributes [{name, rating, note}], ratings grouped by
    rating, and questions [{question, answer}]. v3 scorecards carry no
    candidate_id — use application_id. For a specific candidate, use
    list_scorecards_for_application (search_candidates_by_name →
    list_applications(candidate_id=...) → match application → use its ID).
    """
    params: dict[str, Any] = {"per_page": per_page, "cursor": cursor, "status": status}
    add_date_filter(params, "created_at", gte=created_after, lt=created_before)
    result = await client.harvest_get("/scorecards", params=params, paginate=paginate)
    if client._is_error(result) or not include_details:
        return result
    warnings: list[str] = []
    await _hydrate_scorecards(client, result.get("items", []), warnings)
    return _with_warnings(result, warnings)


async def list_scorecards_for_application(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
) -> dict[str, Any]:
    """List scorecards submitted for a specific application. Read-only.

    To find application_id: search_candidates_by_name →
    list_applications(candidate_id=...) → match the application to the job.
    Returns each interviewer's attribute ratings, question answers, notes and
    overall recommendation (candidate_rating).
    """
    result = await client.harvest_get(
        "/scorecards",
        params={"application_ids": [application_id], "per_page": 500},
        paginate="all",
    )
    if client._is_error(result):
        return result
    warnings: list[str] = []
    await _hydrate_scorecards(client, result.get("items", []), warnings)
    return _with_warnings(result, warnings)


async def get_scorecard(
    client: GreenhouseClient,
    *,
    scorecard_id: Annotated[
        int,
        Field(
            description="Scorecard ID — get from list_scorecards or list_scorecards_for_application"
        ),
    ],
) -> dict[str, Any]:
    """Get a single scorecard by ID. Read-only.

    Returns the interviewer, interview, attribute ratings, question answers,
    notes, and overall recommendation (candidate_rating). To find scorecard
    IDs: list_scorecards_for_application.
    """
    scorecard = await client.harvest_get_by_id("/scorecards", scorecard_id)
    if client._is_error(scorecard):
        return scorecard
    warnings: list[str] = []
    await _hydrate_scorecards(client, [scorecard], warnings)
    return _with_warnings(scorecard, warnings)
