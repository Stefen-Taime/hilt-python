from __future__ import annotations

from datetime import datetime, timezone

import pytest

from hilt.utils.timestamp import now_iso8601, parse_timestamp

UTC = getattr(datetime, "UTC", timezone.utc)


def test_now_iso8601_format() -> None:
    stamp = now_iso8601()
    assert stamp.endswith("Z")
    datetime_obj = parse_timestamp(stamp)
    assert datetime_obj.tzinfo == UTC


def test_parse_timestamp_round_trip() -> None:
    original = "2025-10-08T14:30:45.123Z"
    parsed = parse_timestamp(original)
    assert parsed.year == 2025
    assert parsed.month == 10
    assert parsed.day == 8
    assert parsed.tzinfo == UTC
    assert parse_timestamp(parsed.isoformat()).tzinfo == UTC


def test_parse_timestamp_rejects_empty() -> None:
    with pytest.raises(ValueError):
        parse_timestamp("")
