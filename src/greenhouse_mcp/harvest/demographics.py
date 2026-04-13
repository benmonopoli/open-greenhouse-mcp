"""Harvest API — Demographics tools (11 tools)."""
from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_question_sets(
    client: GreenhouseClient,
) -> dict[str, Any]:
    """List all demographic survey question sets."""
    return await client.harvest_get("/demographics/question_sets")


async def get_question_set(
    client: GreenhouseClient,
    *,
    question_set_id: int,
) -> dict[str, Any]:
    """Get a single demographic question set by ID."""
    return await client.harvest_get_one(f"/demographics/question_sets/{question_set_id}")


async def list_questions(
    client: GreenhouseClient,
) -> dict[str, Any]:
    """List all demographic survey questions."""
    return await client.harvest_get("/demographics/questions")


async def list_questions_for_question_set(
    client: GreenhouseClient,
    *,
    question_set_id: int,
) -> dict[str, Any]:
    """List all demographic questions belonging to a specific question set."""
    return await client.harvest_get(
        f"/demographics/question_sets/{question_set_id}/questions"
    )


async def get_question(
    client: GreenhouseClient,
    *,
    question_id: int,
) -> dict[str, Any]:
    """Get a single demographic question by ID."""
    return await client.harvest_get_one(f"/demographics/questions/{question_id}")


async def list_answer_options(
    client: GreenhouseClient,
) -> dict[str, Any]:
    """List all demographic survey answer options."""
    return await client.harvest_get("/demographics/answer_options")


async def list_answer_options_for_question(
    client: GreenhouseClient,
    *,
    question_id: int,
) -> dict[str, Any]:
    """List all answer options for a specific demographic question."""
    return await client.harvest_get(
        f"/demographics/questions/{question_id}/answer_options"
    )


async def get_answer_option(
    client: GreenhouseClient,
    *,
    answer_option_id: int,
) -> dict[str, Any]:
    """Get a single demographic answer option by ID."""
    return await client.harvest_get_one(f"/demographics/answer_options/{answer_option_id}")


async def list_answers(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    paginate: str = "single",
) -> dict[str, Any]:
    """List all demographic survey answers submitted by candidates."""
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get("/demographics/answers", params=params, paginate=paginate)


async def list_answers_for_application(
    client: GreenhouseClient,
    *,
    application_id: int,
) -> dict[str, Any]:
    """List all demographic survey answers submitted for a specific application."""
    return await client.harvest_get(
        f"/applications/{application_id}/demographics/answers"
    )


async def get_answer(
    client: GreenhouseClient,
    *,
    answer_id: int,
) -> dict[str, Any]:
    """Get a single demographic survey answer by ID."""
    return await client.harvest_get_one(f"/demographics/answers/{answer_id}")
