import os
from unittest.mock import patch

import pytest

from greenhouse_mcp.server import create_server, get_client


class TestGetClient:
    def setup_method(self):
        """Reset client singleton between tests."""
        import greenhouse_mcp.server
        greenhouse_mcp.server._client = None

    @patch.dict(os.environ, {"GREENHOUSE_API_KEY": "test-key"}, clear=False)
    def test_api_key_creates_client(self):
        client = get_client()
        assert client.api_key == "test-key"

    def test_board_token_creates_client(self):
        excluded = ("GREENHOUSE_API_KEY", "GREENHOUSE_BOARD_TOKEN")
        env = {k: v for k, v in os.environ.items() if k not in excluded}
        env["GREENHOUSE_BOARD_TOKEN"] = "my-board"
        with patch.dict(os.environ, env, clear=True):
            client = get_client()
            assert client.board_token == "my-board"

    def test_no_credentials_raises(self):
        excluded = ("GREENHOUSE_API_KEY", "GREENHOUSE_BOARD_TOKEN")
        env = {k: v for k, v in os.environ.items() if k not in excluded}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="GREENHOUSE_API_KEY or GREENHOUSE_BOARD_TOKEN"):
                get_client()

    @patch.dict(os.environ, {
        "GREENHOUSE_API_KEY": "test-key",
        "GREENHOUSE_ON_BEHALF_OF": "user@co.com",
    }, clear=False)
    def test_on_behalf_of_passed(self):
        client = get_client()
        assert client.on_behalf_of == "user@co.com"


class TestCreateServer:
    def test_returns_fastmcp_instance(self):
        server = create_server()
        assert server.name == "Greenhouse"

    @patch.dict(os.environ, {"GREENHOUSE_API_KEY": "test-key"}, clear=False)
    def test_api_key_registers_all_tools(self):
        server = create_server()
        tools = server._tool_manager._tools
        # Should have harvest + board + ingestion + webhook tools
        assert len(tools) > 100
        assert "list_candidates" in tools
        assert "get_board" in tools
        assert "webhook_list_rules" in tools

    def test_no_credentials_still_registers_all_tools(self):
        """Tools are registered at startup for introspection even without credentials."""
        excluded = ("GREENHOUSE_API_KEY", "GREENHOUSE_BOARD_TOKEN")
        env = {k: v for k, v in os.environ.items() if k not in excluded}
        with patch.dict(os.environ, env, clear=True):
            server = create_server()
            tools = list(server._tool_manager._tools.keys())
            # All tools register regardless of credentials (credentials checked at invocation)
            assert "get_board" in tools
            assert "list_board_jobs" in tools
            assert "list_candidates" in tools
            assert "list_jobs" in tools
            assert "screen_candidate" in tools
            assert "fetch_new_applications" in tools
            assert "search_pipeline_candidates" in tools
            assert "scan_all_candidates" in tools
            assert "batch_read_resumes" in tools
            assert "scan_pipeline_resumes" in tools
            assert "webhook_list_rules" in tools
            assert len(tools) > 100
