"""Internal helpers for OpenAI auto-instrumentation."""

from __future__ import annotations

import importlib
import uuid
from functools import lru_cache
from typing import Any

from hilt.core.actor import Actor
from hilt.core.event import Content, Event
from hilt.io.session import Session

HILT_NAMESPACE = uuid.UUID("a8f7e6d5-c4b3-4a21-9f0e-1d2c3b4a5e6f")

MODEL_PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.150, "output": 0.600},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
}


def _calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate API call cost."""
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["gpt-4o-mini"])
    input_cost = (prompt_tokens * pricing["input"]) / 1_000_000
    output_cost = (completion_tokens * pricing["output"]) / 1_000_000
    return input_cost + output_cost


def _generate_conversation_uuid(session_id: str) -> str:
    """Generate deterministic conversation UUID."""
    conversation_uuid = uuid.uuid5(HILT_NAMESPACE, session_id)
    return f"conv_{conversation_uuid.hex[:12]}"


def _extract_status_code(error: Exception) -> int:
    """Extract HTTP status code from error."""
    status_attr = getattr(error, "status_code", None)
    if isinstance(status_attr, int):
        return status_attr

    rate_limit_cls = _get_rate_limit_error()
    if rate_limit_cls is not None and isinstance(error, rate_limit_cls):
        return 429

    error_str = str(error).lower()
    if "429" in error_str or "rate limit" in error_str:
        return 429
    elif "401" in error_str:
        return 401
    elif "403" in error_str:
        return 403
    elif "400" in error_str:
        return 400
    elif "503" in error_str:
        return 503

    return 500


def _unwrap_message_content(message: Any) -> str:
    """Extract text from OpenAI message."""
    content = getattr(message, "content", "")
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict):
                parts.append(str(part.get("text") or part.get("content") or ""))
            else:
                text_attr = getattr(part, "text", None)
                parts.append(str(text_attr if text_attr is not None else part))
        return " ".join(filter(None, parts))
    return str(content)


def _usage_value(usage: Any, key: str) -> int:
    """Extract usage value."""
    if hasattr(usage, key):
        value = getattr(usage, key)
        return int(value or 0)
    if isinstance(usage, dict):
        return int(usage.get(key, 0) or 0)
    return 0


@lru_cache(maxsize=1)
def _get_rate_limit_error() -> type[Exception] | None:
    """Return OpenAI's RateLimitError class if available."""
    try:
        openai_module = importlib.import_module("openai")
    except ImportError:
        return None

    rate_limit_error = getattr(openai_module, "RateLimitError", None)
    if isinstance(rate_limit_error, type) and issubclass(rate_limit_error, Exception):
        return rate_limit_error
    return None


def _log_system_event(
    session: Session,
    *,
    session_id: str,
    reply_to: str,
    error_code: str,
    message: str,
    latency_ms: int | None = None,
    status_code: int = 500,
) -> None:
    """Log system error event."""
    extensions: dict[str, Any] = {
        "reply_to": reply_to,
        "error_code": error_code,
        "status_code": status_code,
    }

    if latency_ms is not None:
        extensions["latency_ms"] = latency_ms

    session.append(
        Event(
            session_id=session_id,
            actor=Actor(type="system", id="openai"),
            action="system",
            content=Content(text=message),
            extensions=extensions,
        )
    )


__all__ = [
    "_calculate_cost",
    "_generate_conversation_uuid",
    "_extract_status_code",
    "_unwrap_message_content",
    "_usage_value",
    "_log_system_event",
]
