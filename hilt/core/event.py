"""HILT Event data model."""

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, ConfigDict


class Actor(BaseModel):
    """Actor of an event (human, agent, tool, system)."""

    type: str = Field(..., pattern="^(human|agent|tool|system)$")
    id: str = Field(..., min_length=1)
    did: Optional[str] = None  # Decentralized Identifier

    model_config = ConfigDict(frozen=True)  # Immutable


class Content(BaseModel):
    """Content of an event."""

    text: Optional[str] = None
    text_hash: Optional[str] = None
    text_encrypted: Optional[str] = None
    media: list[dict[str, Any]] = Field(default_factory=list)


class Metrics(BaseModel):
    """Performance metrics."""

    latency_ms: Optional[int] = None
    tokens: Optional[dict[str, int]] = None  # prompt, completion, total
    cost_usd: Optional[float] = None


class Privacy(BaseModel):
    """Privacy/GDPR information."""

    pii_detected: list[str] = Field(default_factory=list)
    redaction_applied: bool = False
    consent: Optional[dict[str, Any]] = None


class Event(BaseModel):
    """
    HILT Event representing a human-AI interaction.

    Attributes:
        hilt_version: HILT format version
        event_id: Unique identifier (UUID)
        timestamp: ISO 8601 timestamp
        session_id: Session identifier
        actor: Event actor
        action: Action type (prompt, completion, etc.)
        content: Event content
        provenance: Provenance (model, tools)
        metrics: Metrics (latency, tokens, cost)
        privacy: Privacy information
        integrity: Signature and hashes
        extensions: Custom fields

    Example:
        >>> event = Event(
        ...     session_id="sess_123",
        ...     actor=Actor(type="human", id="alice"),
        ...     action="prompt",
        ...     content=Content(text="Hello")
        ... )
        >>> print(event.event_id)
        018c5e9e-87d2-7000-9c4f-a1b2c3d4e5f6
    """

    hilt_version: str = "1.0.0"
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    session_id: str
    actor: Actor
    action: str

    # Optional fields
    content: Optional[Content] = None
    provenance: Optional[dict[str, Any]] = None
    metrics: Optional[Metrics] = None
    privacy: Optional[Privacy] = None
    integrity: Optional[dict[str, Any]] = None
    extensions: Optional[dict[str, Any]] = None

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        """Validate action is one of the allowed types."""
        valid_actions = {
            "prompt",
            "completion",
            "tool_call",
            "tool_result",
            "feedback",
            "retrieval",
            "rerank",
            "embedding",
            "system",
        }
        if v not in valid_actions:
            raise ValueError(f"Invalid action: {v}. Must be one of {valid_actions}")
        return v

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump(exclude_none=True, by_alias=True)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return self.model_dump_json(exclude_none=True, by_alias=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        """Create Event from dictionary."""
        return cls.model_validate(data)

    @classmethod
    def from_json(cls, json_str: str) -> "Event":
        """Create Event from JSON string."""
        return cls.model_validate_json(json_str)

    model_config = ConfigDict(
        extra="allow",  # Allow extra fields (extensions)
        validate_assignment=True  # Validate on assignment
    )