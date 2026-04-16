"""Harvest API — Demographics tools (11 tools)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_question_sets(
    client: GreenhouseClient,
) -> dict[str, Any]:
    """List all demographic survey question sets. Read-only.

    Admin/compliance tool for managing demographic data collection.
    """
    return await client.harvest_get("/demographics/question_sets")


async def get_question_set(
    client: GreenhouseClient,
    *,
    question_set_id: Annotated[int, Field(description="Question set ID — get from list_question_sets")],
) -> dict[str, Any]:
    """Get a demographic question set by ID. Read-only.

    To find IDs: list_question_sets.
    """
    return await client.harvest_get_one(f"/demographics/question_sets/{question_set_id}")


async def list_questions(
    client: GreenhouseClient,
) -> dict[str, Any]:
    """List all demographic survey questions across all sets. Read-only."""
    return await client.harvest_get("/demographics/questions")


async def list_questions_for_question_set(
    client: GreenhouseClient,
    *,
    question_set_id: Annotated[int, Field(description="Question set ID — get from list_question_sets")],
) -> dict[str, Any]:
    """List questions in a specific demographic question set. Read-only.

    To find question_set_id: list_question_sets.
    """
    return await client.harvest_get(
        f"/demographics/question_sets/{question_set_id}/questions"
    )


async def get_question(
    client: GreenhouseClient,
    *,
    question_id: Annotated[int, Field(description="Demographic question ID — get from list_questions")],
) -> dict[str, Any]:
    """Get a demographic question by ID. Read-only.

    To find IDs: list_questions or list_questions_for_question_set.
    """
    return await client.harvest_get_one(f"/demographics/questions/{question_id}")


async def list_answer_options(
    client: GreenhouseClient,
) -> dict[str, Any]:
    """List all demographic answer options across all questions. Read-only."""
    return await client.harvest_get("/demographics/answer_options")


async def list_answer_options_for_question(
    client: GreenhouseClient,
    *,
    question_id: Annotated[int, Field(description="Demographic question ID — get from list_questions")],
) -> dict[str, Any]:
    """List answer options for a specific demographic question. Read-only.

    To find question_id: list_questions or list_questions_for_question_set.
    """
    return await client.harvest_get(
        f"/demographics/questions/{question_id}/answer_options"
    )


async def get_answer_option(
    client: GreenhouseClient,
    *,
    answer_option_id: Annotated[int, Field(description="Answer option ID — get from list_answer_options")],
) -> dict[str, Any]:
    """Get a demographic answer option by ID. Read-only.

    To find IDs: list_answer_options or list_answer_options_for_question.
    """
    return await client.harvest_get_one(f"/demographics/answer_options/{answer_option_id}")


async def list_answers(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    page: Annotated[int, Field(description="Page number (starts at 1)")] = 1,
    paginate: Annotated[str, Field(description="'single' for one page, 'all' to auto-fetch every page")] = "single",
) -> dict[str, Any]:
    """List all demographic survey responses submitted by candidates. Read-only."""
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get("/demographics/answers", params=params, paginate=paginate)


async def list_answers_for_application(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
) -> dict[str, Any]:
    """List demographic responses for a specific application. Read-only.

    To find application_id: search_candidates_by_name → get_candidate →
    match the application to the job.
    """
    return await client.harvest_get(
        f"/applications/{application_id}/demographics/answers"
    )


async def get_answer(
    client: GreenhouseClient,
    *,
    answer_id: Annotated[int, Field(description="Demographic answer ID — get from list_answers")],
) -> dict[str, Any]:
    """Get a single demographic survey response by ID. Read-only.

    To find IDs: list_answers or list_answers_for_application.
    """
    return await client.harvest_get_one(f"/demographics/answers/{answer_id}")
