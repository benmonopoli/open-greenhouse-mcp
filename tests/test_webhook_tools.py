import pytest

from greenhouse_mcp.webhook_receiver.models import WebhookDB


@pytest.fixture
def db(tmp_path):
    return WebhookDB(str(tmp_path / "test.db"))


async def test_webhook_create_and_list_rules(db):
    from greenhouse_mcp.webhook_tools.rules import webhook_create_rule, webhook_list_rules

    await webhook_create_rule(
        db, event_type="hire_candidate", action_type="forward",
        action_url="https://hooks.slack.com/xxx"
    )
    result = await webhook_list_rules(db)
    assert result["total"] == 1


async def test_webhook_list_events():
    from greenhouse_mcp.webhook_tools.events import webhook_list_events

    result = await webhook_list_events()
    assert result["total"] >= 27


async def test_webhook_setup_guide(db):
    from greenhouse_mcp.webhook_tools.setup import webhook_setup_guide

    result = await webhook_setup_guide(db, receiver_url="https://my-app.fly.dev")
    assert "webhooks/greenhouse" in result["values_to_copy"]["endpoint_url"]
    assert len(result["values_to_copy"]["secret_key"]) == 64  # 32 bytes hex
    assert db.get_secret() is not None


async def test_webhook_test_rule_no_events(db):
    from greenhouse_mcp.webhook_tools.rules import webhook_create_rule
    from greenhouse_mcp.webhook_tools.testing import webhook_test_rule

    result = await webhook_create_rule(
        db, event_type="hire_candidate", action_type="log"
    )
    test_result = await webhook_test_rule(db, rule_id=result["rule_id"])
    assert "error" in test_result  # no events to match against
