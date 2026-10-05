"""Harvest API — Demographics tools (11 tools)."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient, add_date_filter


async def list_question_sets(
    client: GreenhouseClient,
) -> dict[str, Any]:
    """List all demographic survey question sets. Read-only.

    Admin/compliance tool for managing demographic data collection. Each set
    has title, description, active and enabled.
    """
    return await client.harvest_get(
        "/demographic_question_sets", params={"per_page": 500}, paginate="all"
    )


async def get_question_set(
    client: GreenhouseClient,
    *,
    question_set_id: Annotated[
        int, Field(description="Question set ID — get from list_question_sets")
    ],
) -> dict[str, Any]:
    """Get a demographic question set by ID. Read-only.

    To find IDs: list_question_sets.
    """
    return await client.harvest_get_by_id("/demographic_question_sets", question_set_id)


async def list_questions(
    client: GreenhouseClient,
) -> dict[str, Any]:
    """List all demographic survey questions across all sets. Read-only.

    Each question has name (the prompt), demographic_question_set_id,
    required, answer_type and sort_order.
    """
    return await client.harvest_get(
        "/demographic_questions", params={"per_page": 500}, paginate="all"
    )


async def list_questions_for_question_set(
    client: GreenhouseClient,
    *,
    question_set_id: Annotated[
        int, Field(description="Question set ID — get from list_question_sets")
    ],
) -> dict[str, Any]:
    """List questions in a specific demographic question set. Read-only.

    To find question_set_id: list_question_sets.
    """
    return await client.harvest_get(
        "/demographic_questions",
        params={"demographic_question_set_ids": [question_set_id], "per_page": 500},
        paginate="all",
    )


async def get_question(
    client: GreenhouseClient,
    *,
    question_id: Annotated[
        int, Field(description="Demographic question ID — get from list_questions")
    ],
) -> dict[str, Any]:
    """Get a demographic question by ID. Read-only.

    To find IDs: list_questions or list_questions_for_question_set.
    """
    return await client.harvest_get_by_id("/demographic_questions", question_id)


async def list_answer_options(
    client: GreenhouseClient,
) -> dict[str, Any]:
    """List all demographic answer options across all questions. Read-only.

    Each option has name, demographic_question_id, free_form,
    decline_to_answer, active and sort_order.
    """
    return await client.harvest_get(
        "/demographic_answer_options", params={"per_page": 500}, paginate="all"
    )


async def list_answer_options_for_question(
    client: GreenhouseClient,
    *,
    question_id: Annotated[
        int, Field(description="Demographic question ID — get from list_questions")
    ],
) -> dict[str, Any]:
    """List answer options for a specific demographic question. Read-only.

    To find question_id: list_questions or list_questions_for_question_set.
    """
    return await client.harvest_get(
        "/demographic_answer_options",
        params={"demographic_question_ids": [question_id], "per_page": 500},
        paginate="all",
    )


async def get_answer_option(
    client: GreenhouseClient,
    *,
    answer_option_id: Annotated[
        int, Field(description="Answer option ID — get from list_answer_options")
    ],
) -> dict[str, Any]:
    """Get a demographic answer option by ID. Read-only.

    To find IDs: list_answer_options or list_answer_options_for_question.
    """
    return await client.harvest_get_by_id("/demographic_answer_options", answer_option_id)


async def list_answers(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    cursor: Annotated[
        str | None,
        Field(description="Pass next_cursor from the previous response to get the next page"),
    ] = None,
    created_after: Annotated[
        str | None, Field(description="ISO 8601 datetime — only answers created after this")
    ] = None,
    paginate: Annotated[
        str, Field(description="'single' for one page, 'all' to auto-fetch every page")
    ] = "single",
) -> dict[str, Any]:
    """List all demographic survey responses submitted by candidates. Read-only.

    Each answer has application_id, demographic_question_id,
    demographic_answer_option_id and free_form_text. Resolve labels with
    list_questions and list_answer_options.
    """
    params: dict[str, Any] = {"per_page": per_page}
    if cursor:
        params["cursor"] = cursor
    add_date_filter(params, "created_at", gt=created_after)
    return await client.harvest_get("/demographic_answers", params=params, paginate=paginate)


async def list_answers_for_application(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
) -> dict[str, Any]:
    """List demographic responses for a specific application. Read-only.

    To find application_id: search_candidates_by_name →
    list_applications(candidate_id=...) → match the application to the job.
    """
    return await client.harvest_get(
        "/demographic_answers",
        params={"application_ids": [application_id], "per_page": 500},
        paginate="all",
    )


async def get_answer(
    client: GreenhouseClient,
    *,
    answer_id: Annotated[int, Field(description="Demographic answer ID — get from list_answers")],
) -> dict[str, Any]:
    """Get a single demographic survey response by ID. Read-only.

    To find IDs: list_answers or list_answers_for_application.
    """
    return await client.harvest_get_by_id("/demographic_answers", answer_id)
