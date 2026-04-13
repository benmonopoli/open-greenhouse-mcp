import hashlib
import hmac
import json

import pytest

from greenhouse_mcp.webhook_receiver.models import WebhookDB


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test_webhooks.db"
    return WebhookDB(str(db_path))


class TestWebhookDB:
    def test_create_rule(self, db):
        rule_id = db.create_rule(
            event_type="hire_candidate",
            action_type="forward",
            action_config={"url": "https://hooks.slack.com/services/xxx"},
        )
        assert rule_id > 0

    def test_list_rules(self, db):
        db.create_rule(event_type="hire_candidate", action_type="forward", action_config={})
        db.create_rule(event_type="reject_candidate", action_type="log", action_config={})
        rules = db.list_rules()
        assert len(rules) == 2

    def test_update_rule(self, db):
        rule_id = db.create_rule(event_type="hire_candidate", action_type="log", action_config={})
        db.update_rule(rule_id, active=False)
        rules = db.list_rules()
        assert rules[0]["active"] == 0

    def test_delete_rule(self, db):
        rule_id = db.create_rule(event_type="hire_candidate", action_type="log", action_config={})
        db.delete_rule(rule_id)
        assert len(db.list_rules()) == 0

    def test_log_event(self, db):
        db.log_event(
            event_type="hire_candidate",
            payload={"action": "hire_candidate", "payload": {"id": 1}},
        )
        events = db.list_recent_events(limit=10)
        assert len(events) == 1
        assert events[0]["event_type"] == "hire_candidate"

    def test_get_matching_rules(self, db):
        db.create_rule(event_type="hire_candidate", action_type="forward", action_config={})
        db.create_rule(event_type="*", action_type="log", action_config={})
        db.create_rule(event_type="reject_candidate", action_type="forward", action_config={})
        matches = db.get_matching_rules("hire_candidate")
        assert len(matches) == 2  # specific + wildcard

    def test_store_and_get_secret(self, db):
        db.store_secret("my-secret-key")
        assert db.get_secret() == "my-secret-key"


class TestHMACVerification:
    def test_verify_signature(self):
        from greenhouse_mcp.webhook_receiver.receiver import verify_signature

        secret = "my-secret"
        body = json.dumps({"action": "hire_candidate"}).encode()
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        header = f"sha256 {expected}"
        assert verify_signature(body, header, secret) is True

    def test_reject_bad_signature(self):
        from greenhouse_mcp.webhook_receiver.receiver import verify_signature

        assert verify_signature(b"body", "sha256 wrong", "secret") is False
