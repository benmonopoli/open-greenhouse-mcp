"""Structured JSON logging for greenhouse-mcp.

Logs to stderr (default) or a file via GREENHOUSE_LOG_FILE.
Log level controlled by GREENHOUSE_LOG_LEVEL (default: warning).

Each log line is a JSON object with at minimum:
    {"ts": "...", "level": "...", "event": "...", "profile": "..."}
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any


class _JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname.lower(),
            "event": record.getMessage(),
        }
        # Merge extra fields passed via logger.info("event", extra={...})
        for key in ("profile", "tools_registered", "method", "url", "status",
                     "latency_ms", "endpoint", "tool", "error"):
            val = getattr(record, key, None)
            if val is not None:
                entry[key] = val
        return json.dumps(entry, default=str)


class _StructuredLogger:
    """Thin wrapper around stdlib logging for structured key-value logging."""

    def __init__(self) -> None:
        self._logger = logging.getLogger("greenhouse_mcp")
        self._logger.propagate = False
        self._configured = False

    def _ensure_configured(self) -> None:
        if self._configured:
            return
        self._configured = True

        level_name = os.environ.get("GREENHOUSE_LOG_LEVEL", "warning").upper()
        level = getattr(logging, level_name, logging.WARNING)
        self._logger.setLevel(level)

        handler: logging.Handler
        log_file = os.environ.get("GREENHOUSE_LOG_FILE")
        if log_file:
            handler = logging.FileHandler(log_file)
        else:
            handler = logging.StreamHandler(sys.stderr)

        handler.setFormatter(_JsonFormatter())
        self._logger.addHandler(handler)

    def _log(self, level: int, event: str, **kwargs: Any) -> None:
        self._ensure_configured()
        self._logger.log(level, event, extra=kwargs)

    def debug(self, event: str, **kwargs: Any) -> None:
        self._log(logging.DEBUG, event, **kwargs)

    def info(self, event: str, **kwargs: Any) -> None:
        self._log(logging.INFO, event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        self._log(logging.WARNING, event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        self._log(logging.ERROR, event, **kwargs)


logger = _StructuredLogger()


def log_api_call(
    *,
    method: str,
    url: str,
    status: int,
    start_time: float,
) -> None:
    """Log a completed API call with latency."""
    latency_ms = round((time.monotonic() - start_time) * 1000, 1)
    level = "info" if status < 400 else "warning" if status < 500 else "error"
    getattr(logger, level)(
        "api_call",
        method=method,
        url=url,
        status=status,
        latency_ms=latency_ms,
    )
