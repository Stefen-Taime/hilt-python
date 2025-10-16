"""JSON Schema definitions for HILT events."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import Any, cast

# JSON Schema for Actor
ACTOR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "type": {"type": "string"},
        "id": {"type": "string"},
        "name": {"type": ["string", "null"]},
        "metadata": {"type": ["object", "null"]},
    },
    "required": ["type", "id"],
    "additionalProperties": False,
}


# JSON Schema for Content
CONTENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "text": {"type": ["string", "null"]},
        "images": {"type": ["array", "null"]},
        "metadata": {"type": ["object", "null"]},
    },
    "additionalProperties": True,
}


# JSON Schema for Metrics
METRICS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "tokens": {
            "type": ["object", "null"],
            "properties": {
                "prompt": {"type": "integer"},
                "completion": {"type": "integer"},
                "total": {"type": "integer"},
            },
        },
        "cost_usd": {"type": ["number", "null"]},
        "latency_ms": {"type": ["integer", "null"]},
    },
    "additionalProperties": True,
}


# JSON Schema for Event
EVENT_SCHEMA: dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "event_id": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
        "session_id": {"type": "string"},
        "actor": ACTOR_SCHEMA,
        "action": {"type": "string"},
        "content": {"oneOf": [CONTENT_SCHEMA, {"type": "null"}]},
        "metrics": {"oneOf": [METRICS_SCHEMA, {"type": "null"}]},
        "provenance": {"type": ["object", "null"]},
        "extensions": {"type": ["object", "null"]},
    },
    "required": ["event_id", "timestamp", "session_id", "actor", "action"],
    "additionalProperties": False,
}


def validate_event(event_dict: dict[str, Any]) -> bool:
    """
    Validate an event dictionary against the schema.

    Args:
        event_dict: Event as dictionary

    Returns:
        True if valid

    Raises:
        ValidationError: If event is invalid
    """
    try:
        jsonschema_module = importlib.import_module("jsonschema")
    except ImportError:
        # jsonschema not installed, skip validation
        return True

    validate_fn = cast(
        Callable[..., Any],
        getattr(jsonschema_module, "validate", None),
    )
    validation_error_cls = cast(
        type[Exception], getattr(jsonschema_module, "ValidationError", Exception)
    )

    if validate_fn is None:
        return True

    try:
        validate_fn(event_dict, EVENT_SCHEMA)
        return True
    except validation_error_cls as exc:
        from hilt.core.exceptions import ValidationError

        raise ValidationError(f"Event validation failed: {exc}") from exc


__all__ = [
    "ACTOR_SCHEMA",
    "CONTENT_SCHEMA",
    "METRICS_SCHEMA",
    "EVENT_SCHEMA",
    "validate_event",
]
