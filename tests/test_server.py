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


class TestUserCentricDescriptions:
    """Verify tool descriptions encode lookup chains for ID resolution."""

    def test_tool_count_stable(self):
        """Total tool count should remain 183."""
        excluded = ("GREENHOUSE_API_KEY", "GREENHOUSE_BOARD_TOKEN", "GREENHOUSE_TOOL_PROFILE")
        env = {k: v for k, v in os.environ.items() if k not in excluded}
        env["GREENHOUSE_API_KEY"] = "test-key"
        with patch.dict(os.environ, env, clear=True):
            server = create_server()
            tools = list(server._tool_manager._tools.keys())
            assert len(tools) == 183, f"Expected 183, got {len(tools)}: check for phantom or missing tools"

    def test_candidate_id_params_mention_search(self):
        """Tools with candidate_id should reference search_candidates_by_name."""
        excluded = ("GREENHOUSE_API_KEY", "GREENHOUSE_BOARD_TOKEN", "GREENHOUSE_TOOL_PROFILE")
        env = {k: v for k, v in os.environ.items() if k not in excluded}
        env["GREENHOUSE_API_KEY"] = "test-key"
        with patch.dict(os.environ, env, clear=True):
            server = create_server()
            tools = server._tool_manager._tools
            # Tools that ARE the search tools or don't need hints
            exempt = {
                "search_candidates_by_name", "search_candidates_by_email",
                "list_candidates", "screen_candidate", "fetch_new_applications",
                "scan_pipeline_resumes", "search_pipeline_candidates",
                "scan_all_candidates", "batch_read_resumes",
            }
            missing = []
            for name, tool in tools.items():
                if name in exempt:
                    continue
                schema = tool.parameters or {}
                props = schema.get("properties", {})
                if "candidate_id" not in props:
                    continue
                desc = (tool.description or "").lower()
                param_desc = (props["candidate_id"].get("description") or "").lower()
                combined = desc + " " + param_desc
                if "search_candidates_by_name" not in combined:
                    missing.append(name)
            assert not missing, f"Tools with candidate_id missing search hint: {missing}"

    def test_job_id_params_mention_list_jobs(self):
        """Tools with job_id should reference list_jobs."""
        excluded = ("GREENHOUSE_API_KEY", "GREENHOUSE_BOARD_TOKEN", "GREENHOUSE_TOOL_PROFILE")
        env = {k: v for k, v in os.environ.items() if k not in excluded}
        env["GREENHOUSE_API_KEY"] = "test-key"
        with patch.dict(os.environ, env, clear=True):
            server = create_server()
            tools = server._tool_manager._tools
            exempt = {
                "list_jobs", "list_board_jobs", "get_board_job",
                "retrieve_ingestion_jobs", "post_tracking_link",
                "submit_application", "post_candidate",
                "pipeline_metrics", "source_effectiveness", "time_to_hire",
                "pipeline_summary", "candidates_needing_action", "stale_applications",
                "fetch_new_applications", "search_pipeline_candidates",
                "scan_pipeline_resumes",
            }
            missing = []
            for name, tool in tools.items():
                if name in exempt:
                    continue
                schema = tool.parameters or {}
                props = schema.get("properties", {})
                if "job_id" not in props:
                    continue
                desc = (tool.description or "").lower()
                param_desc = (props["job_id"].get("description") or "").lower()
                combined = desc + " " + param_desc
                if "list_jobs" not in combined:
                    missing.append(name)
            assert not missing, f"Tools with job_id missing list_jobs hint: {missing}"

    def test_no_empty_docstrings(self):
        """Every registered tool must have a non-empty description."""
        excluded = ("GREENHOUSE_API_KEY", "GREENHOUSE_BOARD_TOKEN", "GREENHOUSE_TOOL_PROFILE")
        env = {k: v for k, v in os.environ.items() if k not in excluded}
        env["GREENHOUSE_API_KEY"] = "test-key"
        with patch.dict(os.environ, env, clear=True):
            server = create_server()
            tools = server._tool_manager._tools
            empty = [name for name, tool in tools.items() if not (tool.description or "").strip()]
            assert not empty, f"Tools with empty descriptions: {empty}"
