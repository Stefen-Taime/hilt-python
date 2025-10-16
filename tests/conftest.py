"""Pytest configuration and fixtures."""


import pytest

from hilt import Actor, Event


@pytest.fixture
def sample_event():
    """Create a basic test event."""
    return Event(session_id="sess_test", actor=Actor(type="human", id="alice"), action="prompt")


@pytest.fixture
def temp_hilt_file(tmp_path):
    """Create a temporary HILT file path."""
    return tmp_path / "test.hilt.jsonl"
