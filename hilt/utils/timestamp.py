"""Timestamp utilities for HILT."""

from __future__ import annotations

from datetime import UTC, datetime


def now_iso8601() -> str:
    """Return the current UTC time formatted as ISO 8601 with millisecond precision.

    Example:
        "2025-10-08T14:30:45.123Z"

    Returns:
        A string representing the current time in ISO 8601 format.
    """
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_timestamp(ts: str) -> datetime:
    """Parse an ISO 8601 timestamp into a timezone-aware datetime instance.

    Args:
        ts: The timestamp string to parse.

    Returns:
        A timezone-aware :class:`datetime.datetime` object in UTC.

    Raises:
        ValueError: If the timestamp cannot be parsed.
    """
    text = ts.strip()
    if not text:
        raise ValueError("Timestamp cannot be empty.")

    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"

    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    return dt.astimezone(UTC)
