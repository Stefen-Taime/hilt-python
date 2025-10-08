"""UUID helpers for HILT events."""

from __future__ import annotations

import uuid


def generate_event_id() -> str:
    """Return a sortable UUID string suitable for HILT events.

    Prefers UUIDv7 when available (Python 3.11+). Falls back to UUID4 on
    older versions of Python by generating a random UUID.

    Returns:
        A string representation of the generated UUID.
    """
    generator = getattr(uuid, "uuid7", None)
    if callable(generator):
        return str(generator())
    return str(uuid.uuid4())
