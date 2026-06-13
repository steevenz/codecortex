"""
Structured logging configuration for production-ready observability.

:project: CodeCortex
:package: Core.Logging.Config
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Core-v1.0
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

def setup_logging(log_level: str = "INFO") -> None:
    Logger.setup(log_level)

class StructuredFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname.lower(),
            "context": record.name,
            "message": record.getMessage(),
        }

        standard_fields = [
            "service",
            "environment",
            "version",
            "user_id",
            "tenant_id",
            "organization_id",
            "workspace_id",
            "request_id",
            "trace_id",
            "error_code",
            "duration_ms",
            "inbound",
            "outbound",
        ]

        for field in standard_fields:
            if hasattr(record, field):
                log_entry[field] = getattr(record, field)

        if hasattr(record, "context") and isinstance(record.context, dict):
            for k, v in record.context.items():
                if k not in log_entry:
                    log_entry[k] = v

        if record.exc_info:
            exc_type = record.exc_info[0].__name__ if record.exc_info and record.exc_info[0] else "Exception"
            exc_val = record.exc_info[1]
            if "error_message" not in log_entry:
                log_entry["error_message"] = str(exc_val) if exc_val is not None else ""

            if os.getenv("ENV", "development").strip().lower() != "production" or os.getenv(
                "CODECORTEX_LOG_STACKTRACE", "0"
            ).strip().lower() in {"1", "true", "yes", "on"}:
                log_entry["stack_trace"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)

class Logger:
    _configured = False

    @classmethod
    def setup(cls, log_level: str = "INFO"):
        if cls._configured:
            return

        project_root = Path(__file__).resolve().parents[3]
        env = os.getenv("ENV", "development").strip().lower()
        date_str = datetime.now().strftime("%Y-%m-%d")

        standard_log_path = project_root / "outputs" / "logs" / env / date_str
        standard_log_path.mkdir(parents=True, exist_ok=True)

        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))

        root_logger.handlers.clear()

        console_format = os.getenv("CODECORTEX_LOG_CONSOLE_FORMAT", "json").strip().lower()
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(StructuredFormatter() if console_format == "json" else logging.Formatter("%(message)s"))
        root_logger.addHandler(console_handler)

        cls._configured = True
