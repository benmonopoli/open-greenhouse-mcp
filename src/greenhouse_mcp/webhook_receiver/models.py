"""SQLite database for webhook rules and event log."""

from __future__ import annotations

import json
import sqlite3
import time
from typing import Any


class WebhookDB:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    filter_config TEXT DEFAULT '{}',
                    action_type TEXT NOT NULL,
                    action_config TEXT NOT NULL,
                    active INTEGER DEFAULT 1,
                    created_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    received_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS secrets (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    secret_key TEXT NOT NULL
                )
            """)

    def create_rule(
        self,
        *,
        event_type: str,
        action_type: str,
        action_config: dict[str, Any],
        filter_config: dict[str, Any] | None = None,
    ) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO rules (event_type, filter_config, action_type,"
                " action_config, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    event_type,
                    json.dumps(filter_config or {}),
                    action_type,
                    json.dumps(action_config),
                    time.time(),
                ),
            )
            return cursor.lastrowid  # type: ignore[return-value]

    def list_rules(self) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM rules ORDER BY id").fetchall()
            return [dict(row) for row in rows]

    def update_rule(
        self,
        rule_id: int,
        *,
        event_type: str | None = None,
        action_type: str | None = None,
        action_config: dict[str, Any] | None = None,
        filter_config: dict[str, Any] | None = None,
        active: bool | None = None,
    ) -> None:
        updates: list[str] = []
        values: list[Any] = []
        if event_type is not None:
            updates.append("event_type = ?")
            values.append(event_type)
        if action_type is not None:
            updates.append("action_type = ?")
            values.append(action_type)
        if action_config is not None:
            updates.append("action_config = ?")
            values.append(json.dumps(action_config))
        if filter_config is not None:
            updates.append("filter_config = ?")
            values.append(json.dumps(filter_config))
        if active is not None:
            updates.append("active = ?")
            values.append(int(active))

        if updates:
            values.append(rule_id)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(f"UPDATE rules SET {', '.join(updates)} WHERE id = ?", values)

    def delete_rule(self, rule_id: int) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM rules WHERE id = ?", (rule_id,))

    def get_matching_rules(self, event_type: str) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM rules WHERE active = 1 AND (event_type = ? OR event_type = '*')",
                (event_type,),
            ).fetchall()
            return [dict(row) for row in rows]

    def log_event(self, *, event_type: str, payload: dict[str, Any]) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO events (event_type, payload, received_at) VALUES (?, ?, ?)",
                (event_type, json.dumps(payload), time.time()),
            )
            return cursor.lastrowid  # type: ignore[return-value]

    def list_recent_events(self, *, limit: int = 50) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM events ORDER BY received_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(row) for row in rows]

    def store_secret(self, secret_key: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO secrets (id, secret_key) VALUES (1, ?)",
                (secret_key,),
            )

    def get_secret(self) -> str | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT secret_key FROM secrets WHERE id = 1").fetchone()
            return row[0] if row else None
