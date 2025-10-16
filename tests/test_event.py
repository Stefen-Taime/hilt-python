"""Tests for Event class."""

import pytest
from hilt import Event, Actor, Content


def test_event_creation_minimal(sample_event):
    """Test event creation with minimal fields."""
    assert sample_event.hilt_version == "1.0.0"
    assert sample_event.session_id == "sess_test"
    assert sample_event.actor.type == "human"
    assert sample_event.action == "prompt"
    assert len(sample_event.event_id) == 36  # UUID format


def test_event_creation_full():
    """Test event creation with all fields."""
    event = Event(
        session_id="sess_test",
        actor=Actor(type="agent", id="gpt-4"),
        action="completion",
        content=Content(text="Hello!"),
    )

    assert event.actor.type == "agent"
    assert event.actor.id == "gpt-4"
    assert event.content is not None
    assert event.content.text == "Hello!"


def test_event_invalid_action():
    """Test that invalid action raises ValueError."""
    with pytest.raises(ValueError, match="Invalid action"):
        Event(
            session_id="sess_test", actor=Actor(type="human", id="alice"), action="invalid_action"
        )


def test_event_invalid_actor_type():
    """Test that invalid actor type raises ValidationError."""
    with pytest.raises(Exception):  # Pydantic ValidationError
        Actor(type="invalid_type", id="test")


def test_event_serialization(sample_event):
    """Test JSON serialization/deserialization."""
    # To JSON
    json_str = sample_event.to_json()
    assert isinstance(json_str, str)
    assert "sess_test" in json_str

    # From JSON
    event2 = Event.from_json(json_str)
    assert event2.event_id == sample_event.event_id
    assert event2.session_id == sample_event.session_id
    assert event2.actor.id == sample_event.actor.id


def test_event_to_dict(sample_event):
    """Test dictionary conversion."""
    event_dict = sample_event.to_dict()

    assert isinstance(event_dict, dict)
    assert event_dict["session_id"] == "sess_test"
    assert event_dict["actor"]["type"] == "human"
    assert event_dict["action"] == "prompt"
