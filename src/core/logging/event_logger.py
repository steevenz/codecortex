"""
Structured event logger — unified logging helper for domain services.

:project: CodeCortex
:package: Core.Logging.Event_logger
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Core-v1.0
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

def log_event(
    level: str,
    event_code: str,
    context: Dict,
    *,
    request_id: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
) -> None:
    """Emit a structured log event.

    Args:
        level: Log level name (``INFO``, ``WARN``, ``ERROR``, ``DEBUG``).
        event_code: Machine-readable event identifier (e.g. ``ANALYSIS_STARTED``).
        context: Arbitrary key-value pairs describing the event.
        request_id: Optional correlation ID for tracing.
        logger: Logger instance. Uses the root logger if None.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    extra: Dict = {"context": context}
    if request_id:
        extra["request_id"] = request_id
    if logger is None:
        logger = logging.getLogger(__name__)
    logger.log(log_level, f"[{event_code}] %s", context, extra=extra)

class LoggingMixin:
    """Mixin providing standardised ``_log_event`` for domain services.

    Usage::

        class MyService(LoggingMixin):
            def __init__(self):
                self.logger = logging.getLogger(__name__)

            def do_work(self):
                self._log_event("INFO", "WORK_START", {"key": "val"})

    The mixin reads ``self.logger`` for the logger instance.
    Falls back to the root ``codecortex`` logger if not set.
    """

    def _log_event(
        self,
        level: str,
        event_code: str,
        context: Dict,
        request_id: Optional[str] = None,
    ) -> None:
        log_event(
            level, event_code, context,
            request_id=request_id,
            logger=getattr(self, "logger", None),
        )
