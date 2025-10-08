"""Tests for Session class."""

import pytest
from pathlib import Path

from hilt import Session, Event, Actor, HILTError


def test_session_write_single_event(temp_hilt_file):
    """Test writing a single event."""
    with Session(temp_hilt_file) as session:
        event = Event(
            session_id="sess_test",
            actor=Actor(type="human", id="alice"),
            action="prompt"
        )
        session.append(event)
    
    # Verify file exists
    assert temp_hilt_file.exists()
    
    # Verify content
    content = temp_hilt_file.read_text()
    assert "sess_test" in content
    assert "alice" in content


def test_session_write_multiple_events(temp_hilt_file):
    """Test writing multiple events."""
    with Session(temp_hilt_file) as session:
        for i in range(5):
            event = Event(
                session_id="sess_test",
                actor=Actor(type="human", id=f"user_{i}"),
                action="prompt"
            )
            session.append(event)
    
    # Read back and count
    session = Session(temp_hilt_file, mode="r")
    events = list(session.read())
    
    assert len(events) == 5
    assert events[0].actor.id == "user_0"
    assert events[4].actor.id == "user_4"


def test_session_read_events(temp_hilt_file):
    """Test reading events."""
    # Write events
    with Session(temp_hilt_file) as session:
        for i in range(3):
            event = Event(
                session_id="sess_test",
                actor=Actor(type="human", id=f"user_{i}"),
                action="prompt" if i % 2 == 0 else "completion"
            )
            session.append(event)
    
    # Read events
    session = Session(temp_hilt_file, mode="r")
    events = list(session.read())
    
    assert len(events) == 3
    assert events[0].action == "prompt"
    assert events[1].action == "completion"
    assert events[2].action == "prompt"


def test_session_not_opened_error(temp_hilt_file):
    """Test error when appending to unopened session."""
    session = Session(temp_hilt_file)
    event = Event(
        session_id="sess_test",
        actor=Actor(type="human", id="alice"),
        action="prompt"
    )
    
    with pytest.raises(HILTError, match="Session not opened"):
        session.append(event)


def test_session_file_not_found():
    """Test error when reading non-existent file."""
    session = Session("nonexistent.hilt.jsonl", mode="r")
    
    with pytest.raises(HILTError, match="File not found"):
        list(session.read())


def test_session_creates_directories(tmp_path):
    """Test that session creates parent directories."""
    filepath = tmp_path / "subdir" / "logs" / "test.hilt.jsonl"
    
    with Session(filepath) as session:
        event = Event(
            session_id="sess_test",
            actor=Actor(type="human", id="alice"),
            action="prompt"
        )
        session.append(event)
    
    assert filepath.exists()
    assert filepath.parent.exists()