"""Harvest API — Demographics tools (11 tools)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_question_sets(
    client: GreenhouseClient,
) -> dict[str, Any]:
    """List all demographic survey question sets. Read-only.

    Returns configured demographic survey groups. For questions within a set, use
    list_questions_for_question_set. Demographics are collected separately from
    candidate profile data.
    """
    return await client.harvest_get("/demographics/question_sets")


async def get_question_set(
    client: GreenhouseClient,
    *,
    question_set_id: Annotated[int, Field(description="Question set ID — get from list_question_sets")],
) -> dict[str, Any]:
    """Get a single demographic question set by ID. Read-only.

    Returns the set name and configuration. Use list_question_sets to find IDs.
    For questions in this set, use list_questions_for_question_set.
    """
    return await client.harvest_get_one(f"/demographics/question_sets/{question_set_id}")


async def list_questions(
    client: GreenhouseClient,
) -> dict[str, Any]:
    """List all demographic survey questions across all question sets. Read-only.

    For questions in a specific set, use list_questions_for_question_set instead.
    For answer options on a question, use list_answer_options_for_question.
    """
    return await client.harvest_get("/demographics/questions")


async def list_questions_for_question_set(
    client: GreenhouseClient,
    *,
    question_set_id: Annotated[int, Field(description="Question set ID — get from list_question_sets")],
) -> dict[str, Any]:
    """List all demographic questions in a specific question set. Read-only.

    For all questions across all sets, use list_questions. For answer options on a
    question, use list_answer_options_for_question.
    """
    return await client.harvest_get(
        f"/demographics/question_sets/{question_set_id}/questions"
    )


async def get_question(
    client: GreenhouseClient,
    *,
    question_id: Annotated[int, Field(description="Demographic question ID — get from list_questions")],
) -> dict[str, Any]:
    """Get a single demographic question by ID. Read-only.

    Returns the question text and type. For answer options, use
    list_answer_options_for_question.
    """
    return await client.harvest_get_one(f"/demographics/questions/{question_id}")


async def list_answer_options(
    client: GreenhouseClient,
) -> dict[str, Any]:
    """List all demographic survey answer options across all questions. Read-only.

    For options on a specific question, use list_answer_options_for_question instead.
    """
    return await client.harvest_get("/demographics/answer_options")


async def list_answer_options_for_question(
    client: GreenhouseClient,
    *,
    question_id: Annotated[int, Field(description="Demographic question ID — get from list_questions")],
) -> dict[str, Any]:
    """List all answer options for a specific demographic question. Read-only.

    Returns the valid choices for this question. For all options across all questions,
    use list_answer_options.
    """
    return await client.harvest_get(
        f"/demographics/questions/{question_id}/answer_options"
    )


async def get_answer_option(
    client: GreenhouseClient,
    *,
    answer_option_id: Annotated[int, Field(description="Answer option ID — get from list_answer_options")],
) -> dict[str, Any]:
    """Get a single demographic answer option by ID. Read-only.

    Returns the option text and associated question.
    """
    return await client.harvest_get_one(f"/demographics/answer_options/{answer_option_id}")


async def list_answers(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    page: Annotated[int, Field(description="Page number (starts at 1)")] = 1,
    paginate: Annotated[str, Field(description="'single' for one page, 'all' to auto-fetch every page")] = "single",
) -> dict[str, Any]:
    """List all demographic survey answers submitted by candidates. Read-only.

    Returns answers globally. For answers on a specific application, use
    list_answers_for_application. Demographic answers are separate from screening
    question answers (which are on the application record).
    """
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get("/demographics/answers", params=params, paginate=paginate)


async def list_answers_for_application(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
) -> dict[str, Any]:
    """List all demographic survey answers for a specific application. Read-only.

    For all answers globally, use list_answers. For screening question answers
    (not demographics), see the application record via get_application.
    """
    return await client.harvest_get(
        f"/applications/{application_id}/demographics/answers"
    )


async def get_answer(
    client: GreenhouseClient,
    *,
    answer_id: Annotated[int, Field(description="Demographic answer ID — get from list_answers")],
) -> dict[str, Any]:
    """Get a single demographic survey answer by ID. Read-only.

    Returns the answer value, associated question, and application.
    """
    return await client.harvest_get_one(f"/demographics/answers/{answer_id}")
