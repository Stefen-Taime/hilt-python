"""Helpers to log Anthropic Claude interactions to HILT."""

from __future__ import annotations

from typing import Any, Iterable, Optional

from hilt import Actor, Content, Event, Metrics, Session


def log_claude_interaction(
    session: Session,
    *,
    user_message: str,
    response: Any,
    session_id: str = "claude_session",
    user_id: str = "user",
    assistant_id: str = "claude",
) -> None:
    """Record a single Claude prompt/response pair in HILT.

    Args:
        session: The HILT :class:`~hilt.io.session.Session` to write to.
        user_message: Plain-text message sent to Claude.
        response: Claude API response object (dict or SDK object).
        session_id: Identifier for the conversation session.
        user_id: Actor ID to use for the human speaker.
        assistant_id: Actor ID for Claude.
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
                "prompt": usage.get("input_tokens", 0),
                "completion": usage.get("output_tokens", 0),
                "total": usage.get("total_tokens")
                or (usage.get("input_tokens", 0) + usage.get("output_tokens", 0)),
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
    content = _get(response, "content", default=[])
    if isinstance(content, str):
        return content
    if isinstance(content, Iterable):
        for block in content:
            text = _get(block, "text")
            if text:
                return text
    completion = _get(response, "completion")
    if isinstance(completion, str):
        return completion
    return ""


def _extract_usage(response: Any) -> Optional[dict[str, int]]:
    usage = _get(response, "usage")
    if not usage:
        return None
    return {
        "input_tokens": int(_get(usage, "input_tokens", default=0)),
        "output_tokens": int(_get(usage, "output_tokens", default=0)),
        "total_tokens": int(_get(usage, "total_tokens", default=0)),
    }


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)

