"""
JSON structured logging for WSIP.

Usage:
    from app.logging_config import configure_logging
    configure_logging()          # call once at app startup

Every log record is emitted as a single JSON line:
    {"ts": "2026-04-08T12:00:00", "level": "INFO", "logger": "wsip.request",
     "msg": "GET /health → 200 (3ms)", "request_id": "a1b2c3d4"}
"""

import json
import logging
import sys
from datetime import datetime, timezone


class _JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Attach request_id if the caller embedded it in the record
        if hasattr(record, "request_id"):
            payload["request_id"] = record.request_id
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(level: int = logging.INFO) -> None:
    """Configure root logger with JSON output to stdout.

    Safe to call multiple times — subsequent calls are no-ops because
    the root logger's handlers are only added once.
    """
    root = logging.getLogger()
    if root.handlers:
        return  # already configured

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JSONFormatter())
    root.setLevel(level)
    root.addHandler(handler)

    # Quieten noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
