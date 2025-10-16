"""Event model for HILT."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Union

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

    text: Optional[str] = None
    images: Optional[list] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"


class Metrics(BaseModel):
    """Metrics associated with an event."""

    tokens: Optional[Dict[str, int]] = None
    cost_usd: Optional[float] = None
    latency_ms: Optional[int] = None

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
    actor: Union[Actor, Dict[str, Any]]
    action: str
    content: Union[Content, Dict[str, Any], None] = None
    metrics: Optional[Metrics] = None
    provenance: Optional[Dict[str, Any]] = None
    extensions: Optional[Dict[str, Any]] = None

    @field_validator("actor", mode="before")
    @classmethod
    def validate_actor(cls, v):
        """Convert dict to Actor if needed."""
        if isinstance(v, dict):
            return Actor(**v)
        return v

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v not in ALLOWED_ACTIONS:
            raise ValueError(f"Invalid action '{v}'. Allowed actions: {sorted(ALLOWED_ACTIONS)}")
        return v

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, v):
        """Convert dict to Content if needed."""
        if v is None:
            return None
        if isinstance(v, dict):
            return Content(**v)
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert Event to dictionary."""
        result = {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "actor": self.actor.to_dict() if isinstance(self.actor, Actor) else self.actor,
            "action": self.action,
        }

        if self.content:
            result["content"] = (
                self.content.model_dump(exclude_none=True)
                if isinstance(self.content, Content)
                else self.content
            )

        if self.metrics:
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
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create Event from dictionary."""
        # Parse timestamp if it's a string
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))

        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "Event":
        """Create Event from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    class Config:
        arbitrary_types_allowed = True


__all__ = ["Event", "Content", "Metrics"]
