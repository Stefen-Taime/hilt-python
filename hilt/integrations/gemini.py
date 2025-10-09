"""Helpers to log Google Gemini interactions to HILT."""

from __future__ import annotations

from typing import Any, Iterable, Optional

from hilt import Actor, Content, Event, Metrics, Session


def log_gemini_interaction(
    session: Session,
    *,
    user_message: str,
    response: Any,
    session_id: str = "gemini_session",
    user_id: str = "user",
    assistant_id: str = "gemini",
) -> None:
    """Record a Gemini prompt/response pair in HILT.

    Args:
        session: HILT :class:`~hilt.io.session.Session` used to persist events.
        user_message: Text prompt sent to Gemini.
        response: Gemini SDK response object (dict-like or namespace).
        session_id: Identifier for the conversation session.
        user_id: Actor ID for the human speaker.
        assistant_id: Actor ID for Gemini.
    """

    session.append(
        Event(
            session_id=session_id,
            actor=Actor(type="human", id=user_id),
            action="prompt",
            content=Content(text=user_message),
        )
    )

    text = _extract_text(response)
    usage = _extract_usage(response)
    metrics = None
    if usage:
        metrics = Metrics(
            tokens={
                "prompt": usage.get("prompt_tokens", 0),
                "completion": usage.get("completion_tokens", 0),
                "total": usage.get("total_tokens")
                or (usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)),
            }
        )

    session.append(
        Event(
            session_id=session_id,
            actor=Actor(type="agent", id=assistant_id),
            action="completion",
            content=Content(text=text),
            metrics=metrics,
        )
    )


def _extract_text(response: Any) -> str:
    candidates = _get(response, "candidates", default=[])
    if isinstance(candidates, Iterable):
        for candidate in candidates:
            parts = _get(candidate, "content", default={})
            if parts:
                parts = _get(parts, "parts", default=parts)
            else:
                parts = _get(candidate, "parts", default=[])
            if isinstance(parts, Iterable):
                for part in parts:
                    text = _get(part, "text")
                    if text:
                        return text
    text = _get(response, "text")
    if isinstance(text, str):
        return text
    return ""


def _extract_usage(response: Any) -> Optional[dict[str, int]]:
    usage = _get(response, "usageMetadata") or _get(response, "usage_metadata")
    if not usage:
        return None
    return {
        "prompt_tokens": int(_get(usage, "promptTokenCount", default=0)),
        "completion_tokens": int(
            _get(usage, "candidatesTokenCount", default=_get(usage, "completionTokenCount", default=0))
        ),
        "total_tokens": int(_get(usage, "totalTokenCount", default=0)),
    }


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)

