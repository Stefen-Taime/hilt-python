"""Timestamp utilities for HILT."""

from __future__ import annotations

from datetime import datetime, timezone


def get_utc_timestamp() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


def now_iso8601() -> str:
    """Get the current UTC timestamp as ISO 8601 string with trailing 'Z'."""
    return get_utc_timestamp().isoformat().replace("+00:00", "Z")


def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse ISO format timestamp string."""
    return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))


__all__ = ["get_utc_timestamp", "now_iso8601", "parse_timestamp"]
