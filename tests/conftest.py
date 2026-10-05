import os

import pytest
import respx

from greenhouse_mcp.client import GreenhouseClient

# Keep the developer's real Greenhouse environment out of the test run: server.py
# builds the server at import time and would otherwise call the live API.
for _var in (
    "GREENHOUSE_CLIENT_ID",
    "GREENHOUSE_CLIENT_SECRET",
    "GREENHOUSE_USER_ID",
    "GREENHOUSE_ON_BEHALF_OF",
    "GREENHOUSE_API_KEY",
    "GREENHOUSE_TOOL_PROFILE",
    "GREENHOUSE_READ_ONLY",
    "GREENHOUSE_BOARD_TOKEN",
    "GREENHOUSE_BOARD_API_KEY",
    "GREENHOUSE_INGESTION_API_KEY",
):
    os.environ.pop(_var, None)

HARVEST_BASE = "https://harvest.greenhouse.io/v3"


def make_client(**kwargs):
    """A Harvest v3 client with test credentials and pre-seeded access tokens, so
    tool tests only mock the Harvest endpoints they exercise."""
    kwargs.setdefault("client_id", "test-client-id")
    kwargs.setdefault("client_secret", "test-client-secret")
    c = GreenhouseClient(**kwargs)
    for sub in {"", c.user_id or ""}:
        c._tokens[sub] = ("test-token", float("inf"))
    return c


@pytest.fixture
def client():
    return make_client()


@pytest.fixture
def board_client():
    return GreenhouseClient(board_token="test-board")


@pytest.fixture
def mock_api():
    with respx.mock(assert_all_called=False) as respx_mock:
        yield respx_mock
