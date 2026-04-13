import pytest
import respx

from greenhouse_mcp.client import GreenhouseClient


@pytest.fixture
def api_key():
    return "test-api-key-12345"


@pytest.fixture
def client(api_key):
    return GreenhouseClient(api_key=api_key)


@pytest.fixture
def board_client():
    return GreenhouseClient(board_token="test-board")


@pytest.fixture
def mock_api():
    with respx.mock(assert_all_called=False) as respx_mock:
        yield respx_mock
