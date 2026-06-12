"""
Error classes for CodeCortex.

:project: CodeCortex
:package: Core.Errors.Errors
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Core-v1.0
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

class ApiError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 400,
        error_code: str = "ERR_400",
        details: Optional[dict] = None,
    ):
        super().__init__(message)
        self.status_code = int(status_code)
        self.error_code = str(error_code)
        self.details = details or {}

class DomainError(ApiError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 400,
        error_code: str = "ERR_DOMAIN",
        details: Optional[dict] = None,
    ):
        super().__init__(message, status_code=status_code, error_code=error_code, details=details)

class ValidationError(DomainError):
    def __init__(
        self,
        message: str,
        *,
        field: Optional[str] = None,
        value: Any = None,
        details: Optional[dict] = None,
    ):
        super().__init__(message, status_code=400, error_code="ERR_VALIDATION", details=details)
        if field:
            self.details["field"] = field
        if value is not None:
            self.details["value"] = value

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

def api_response(
    success: bool,
    status_code: int,
    message: str,
    data: Optional[Any] = None,
    request_id: Optional[str] = None,
    error_code: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    details: Optional[Dict[str, Any]] = None,
    insight: Any = None,
    duration_ms: Optional[int] = None,
    start_time: Optional[float] = None,
) -> Dict[str, Any]:
    """Build a standardized API response.

    ``insight`` can be:
    - ``None``: No insight field in response.
    - A ``dict``: Used directly as the insight value.
    - A ``str`` (tool name): Auto-generates insight from ``data`` using the
      registered generator in ``src.core.insight``.

    ``duration_ms``: Explicit duration in milliseconds. Overrides ``start_time``.
    ``start_time``: ``time.monotonic()`` timestamp — computes duration automatically.

    See ``src.core.insight.AIInsight`` for the canonical schema.
    """
    _meta: Dict[str, Any] = {
        "timestamp": _utc_now_iso(),
    }
    if request_id is not None:
        _meta["request_id"] = request_id
    if not success and error_code is not None:
        _meta["error_code"] = error_code
    if duration_ms is not None:
        _meta["duration_ms"] = duration_ms
    elif start_time is not None:
        _meta["duration_ms"] = int((time.monotonic() - start_time) * 1000)
    if details is not None:
        _meta.update(details)
    if meta is not None:
        _meta.update(meta)

    # Auto-generate insight from registered generator if tool name given
    if isinstance(insight, str) and success and data is not None:
        from src.core.insight import generate_insight
        try:
            insight = generate_insight(insight, data).to_dict()
        except Exception:
            insight = None

    response: Dict[str, Any] = {
        "success": success,
        "status_code": status_code,
        "message": message,
        "data": data,
        "meta": _meta,
    }
    if insight is not None:
        response["insight"] = insight
    if request_id is not None:
        response["request_id"] = request_id
    if not success and error_code is not None:
        response["error_code"] = error_code
    return response

def extract_pagination(payload: dict) -> tuple[dict, dict | None]:
    """Extract pagination metadata from a payload dict.

    Removes cursor/metadata keys (``next_cursor``, ``has_more``, ``total``)
    from the data payload and returns them as a separate pagination dict.

    Args:
        payload: Raw payload dict possibly containing pagination keys.

    Returns:
        (clean_payload, pagination_or_none).
    """
    pagination_keys = {"next_cursor", "has_more", "total", "page", "per_page", "total_pages"}
    pagination = {}
    clean = {}
    for k, v in payload.items():
        if k in pagination_keys:
            pagination[k] = v
        else:
            clean[k] = v
    return clean, (pagination if pagination else None)
