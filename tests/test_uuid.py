from __future__ import annotations

import uuid

from hilt.utils.uuid import generate_event_id


def test_generate_event_id_returns_valid_uuid() -> None:
    event_id = generate_event_id()

    parsed = uuid.UUID(event_id)
    assert str(parsed) == event_id


def test_generate_event_id_unique() -> None:
    first = generate_event_id()
    second = generate_event_id()

    assert first != second

