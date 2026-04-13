"""FastMCP server with tool registration and CLI entry point."""

from __future__ import annotations

import functools
import inspect
import os
import sys

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from greenhouse_mcp.client import GreenhouseClient

load_dotenv()

_client: GreenhouseClient | None = None


def get_client() -> GreenhouseClient:
    """Get or create the shared Greenhouse client."""
    global _client
    if _client is not None:
        return _client

    api_key = os.environ.get("GREENHOUSE_API_KEY")
    board_token = os.environ.get("GREENHOUSE_BOARD_TOKEN")
    on_behalf_of = os.environ.get("GREENHOUSE_ON_BEHALF_OF")

    if not api_key and not board_token:
        raise ValueError(
            "At least one of GREENHOUSE_API_KEY or GREENHOUSE_BOARD_TOKEN is required.\n"
            "Harvest API key: Configure > Dev Center > API Credential Management in Greenhouse.\n"
            "Board token: your public job board URL slug."
        )

    _client = GreenhouseClient(
        api_key=api_key,
        board_token=board_token,
        on_behalf_of=on_behalf_of,
    )
    return _client


def _make_tool_wrapper(fn):
    """Create a wrapper that injects get_client() and has the correct signature."""

    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        client = get_client()
        return await fn(client, *args, **kwargs)

    # Remove the `client` parameter from the signature so FastMCP
    # doesn't expose it as a tool parameter.
    orig_sig = inspect.signature(fn)
    params = [p for p in orig_sig.parameters.values() if p.name != "client"]
    wrapper.__signature__ = orig_sig.replace(parameters=params)
    return wrapper


def create_server() -> FastMCP:
    """Create and configure the FastMCP server with all tools."""
    mcp = FastMCP("Greenhouse")
    mcp.description = "Comprehensive MCP server for the full Greenhouse API (~156 tools)"

    # --- Harvest tools ---
    from greenhouse_mcp.harvest import (
        activity_feed,
        applications,
        approvals,
        candidates,
        close_reasons,
        custom_fields,
        demographics,
        departments,
        education,
        eeoc,
        email_templates,
        hiring_team,
        interviews,
        job_openings,
        job_posts,
        job_stages,
        jobs,
        offers,
        offices,
        prospect_pools,
        rejection_reasons,
        scorecards,
        sources,
        tags,
        tracking_links,
        user_permissions,
        user_roles,
        users,
    )

    harvest_modules = [
        candidates, applications, jobs, job_posts, job_stages, job_openings,
        offers, scorecards, interviews, users, user_permissions, departments,
        offices, custom_fields, sources, rejection_reasons, email_templates,
        tags, activity_feed, eeoc, demographics, approvals, hiring_team,
        prospect_pools, close_reasons, tracking_links, user_roles, education,
    ]

    # --- Job Board tools ---
    from greenhouse_mcp.job_board import (
        applications as board_applications,
    )
    from greenhouse_mcp.job_board import (
        board,
    )
    from greenhouse_mcp.job_board import (
        departments as board_departments,
    )
    from greenhouse_mcp.job_board import (
        educations as board_educations,
    )
    from greenhouse_mcp.job_board import (
        jobs as board_jobs,
    )
    from greenhouse_mcp.job_board import (
        offices as board_offices,
    )
    from greenhouse_mcp.job_board import (
        prospects as board_prospects,
    )

    board_modules = [
        board, board_jobs, board_departments, board_offices,
        board_prospects, board_educations, board_applications,
    ]

    # --- Ingestion tools ---
    from greenhouse_mcp.ingestion import (
        candidates as ing_candidates,
    )
    from greenhouse_mcp.ingestion import (
        jobs as ing_jobs,
    )
    from greenhouse_mcp.ingestion import (
        prospects as ing_prospects,
    )
    from greenhouse_mcp.ingestion import (
        retrieve as ing_retrieve,
    )
    from greenhouse_mcp.ingestion import (
        tracking as ing_tracking,
    )
    from greenhouse_mcp.ingestion import (
        users as ing_users,
    )

    ingestion_modules = [
        ing_candidates, ing_jobs, ing_prospects, ing_retrieve,
        ing_tracking, ing_users,
    ]

    all_modules = harvest_modules + board_modules + ingestion_modules

    for module in all_modules:
        for name, fn in inspect.getmembers(module, inspect.isfunction):
            if name.startswith("_"):
                continue
            wrapper = _make_tool_wrapper(fn)
            mcp.tool(name=name, description=fn.__doc__ or name)(wrapper)

    # --- Webhook tools ---
    from pathlib import Path

    from greenhouse_mcp.webhook_receiver.models import WebhookDB
    from greenhouse_mcp.webhook_tools import events, rules, setup, testing

    _webhook_db: WebhookDB | None = None

    def get_webhook_db() -> WebhookDB:
        nonlocal _webhook_db
        if _webhook_db is None:
            db_path = os.environ.get(
                "WEBHOOK_DB_PATH",
                str(Path.home() / ".open-greenhouse-mcp" / "webhooks.db"),
            )
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            _webhook_db = WebhookDB(db_path)
        return _webhook_db

    def _make_webhook_tool_wrapper(fn):
        """Create a wrapper that injects get_webhook_db() and has the correct signature."""

        @functools.wraps(fn)
        async def wrapper(*args, _fn=fn, **kwargs):
            db = get_webhook_db()
            return await _fn(db, *args, **kwargs)

        orig_sig = inspect.signature(fn)
        params = [p for p in orig_sig.parameters.values() if p.name != "db"]
        wrapper.__signature__ = orig_sig.replace(parameters=params)
        return wrapper

    webhook_modules = [rules, events, testing, setup]
    for module in webhook_modules:
        for name, fn in inspect.getmembers(module, inspect.isfunction):
            if name.startswith("_") or not name.startswith("webhook_"):
                continue

            sig = inspect.signature(fn)
            params = list(sig.parameters.values())

            if params and params[0].name == "db":
                wrapper = _make_webhook_tool_wrapper(fn)
                mcp.tool(name=name, description=fn.__doc__ or name)(wrapper)
            else:
                # No db parameter (like webhook_list_events)
                mcp.tool(name=name, description=fn.__doc__ or name)(fn)

    return mcp


# Global server instance
mcp = create_server()


def main() -> None:
    """CLI entry point."""
    try:
        get_client()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    mcp.run()
