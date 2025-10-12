"""Timestamp utilities for HILT."""

from __future__ import annotations

from datetime import datetime, timezone


def get_utc_timestamp() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse ISO format timestamp string."""
    return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))


__all__ = ["get_utc_timestamp", "parse_timestamp"]