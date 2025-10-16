"""Event model for HILT."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from hilt.core.actor import Actor
from hilt.utils.timestamp import get_utc_timestamp

ALLOWED_ACTIONS = {
    "prompt",
    "completion",
    "completion_chunk",
    "retrieval",
    "tool_call",
    "tool_result",
    "system",
    "feedback",
}


class Content(BaseModel):
    """Content of an event (text, images, etc.)."""

    text: str | None = None
    images: list[Any] | None = None
    metadata: dict[str, Any] | None = None

    class Config:
        extra = "allow"


class Metrics(BaseModel):
    """Metrics associated with an event."""

    tokens: dict[str, int] | None = None
    cost_usd: float | None = None
    latency_ms: int | None = None

    class Config:
        extra = "allow"


class Event(BaseModel):
    """
    Core event model for HILT.

    Represents a single interaction in a conversation.
    """

    hilt_version: str = Field(default="1.0.0")
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=get_utc_timestamp)
    session_id: str
    actor: Actor
    action: str
    content: Content | None = None
    metrics: Metrics | None = None
    provenance: dict[str, Any] | None = None
    extensions: dict[str, Any] | None = None

    @field_validator("actor", mode="before")
    @classmethod
    def validate_actor(cls, value: Actor | dict[str, Any]) -> Actor:
        """Convert dict to Actor if needed."""
        if isinstance(value, Actor):
            return value
        if isinstance(value, dict):
            return Actor(**value)
        raise TypeError("actor must be an Actor or mapping")

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v not in ALLOWED_ACTIONS:
            raise ValueError(f"Invalid action '{v}'. Allowed actions: {sorted(ALLOWED_ACTIONS)}")
        return v

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, value: Content | dict[str, Any] | None) -> Content | None:
        """Convert dict to Content if needed."""
        if value is None:
            return None
        if isinstance(value, Content):
            return value
        if isinstance(value, dict):
            return Content(**value)
        raise TypeError("content must be Content, mapping, or None")

    def to_dict(self) -> dict[str, Any]:
        """Convert Event to dictionary."""
        result = {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "actor": self.actor.to_dict(),
            "action": self.action,
        }

        if self.content is not None:
            result["content"] = self.content.model_dump(exclude_none=True)

        if self.metrics is not None:
            result["metrics"] = self.metrics.model_dump(exclude_none=True)

        if self.provenance:
            result["provenance"] = self.provenance

        if self.extensions:
            result["extensions"] = self.extensions

        return result

    def to_json(self) -> str:
        """Convert Event to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Event:
        """Create Event from dictionary."""
        # Parse timestamp if it's a string
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))

        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> Event:
        """Create Event from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    class Config:
        arbitrary_types_allowed = True


__all__ = ["Event", "Content", "Metrics"]
