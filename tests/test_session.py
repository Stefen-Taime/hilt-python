"""Additional tests for Session column filtering functionality.

This file REPLACES the old test that assumed the local backend ignored `columns`.
"""

import json
import pytest
from pathlib import Path
from hilt import Session, Event, Actor, Content, Metrics, HILTError


# ============================================================================
# NEW TESTS FOR LOCAL BACKEND COLUMN FILTERING
# ============================================================================

def test_session_local_backend_with_columns(temp_hilt_file: Path):
    """Local backend accepts and uses columns parameter."""
    custom_columns = ['timestamp', 'speaker', 'action', 'cost_usd']

    with Session(
        backend="local",
        filepath=temp_hilt_file,
        columns=custom_columns
    ) as session:
        assert session.columns == custom_columns

        event = Event(
            session_id="test_session",
            actor=Actor(type="human", id="user"),
            action="prompt",
            content=Content(text="This is a secret message"),
            metrics=Metrics(cost_usd=0.00123)
        )
        session.append(event)

    data = json.loads(temp_hilt_file.read_text().splitlines()[0])

    # Only the 4 custom columns should be present
    assert set(data.keys()) == set(custom_columns)
    assert 'timestamp' in data
    assert 'speaker' in data
    assert 'action' in data
    assert 'cost_usd' in data

    # Full event structure must not be there
    assert 'event_id' not in data
    assert 'session_id' not in data
    assert 'actor' not in data
    assert 'content' not in data
    assert 'metrics' not in data


def test_session_local_backend_without_columns(temp_hilt_file: Path):
    """Local backend writes full events when columns=None."""
    with Session(backend="local", filepath=temp_hilt_file) as session:
        assert session.columns is None
        event = Event(
            session_id="test_session",
            actor=Actor(type="human", id="user"),
            action="prompt",
            content=Content(text="Full message content"),
            metrics=Metrics(cost_usd=0.00123)
        )
        session.append(event)

    data = json.loads(temp_hilt_file.read_text().splitlines()[0])

    # Full event structure present
    assert 'event_id' in data
    assert 'timestamp' in data
    assert 'session_id' in data
    assert 'actor' in data
    assert 'action' in data
    assert 'content' in data
    assert data['content']['text'] == "Full message content"
    assert 'metrics' in data
    assert data['metrics']['cost_usd'] == "0.001230"
    assert data['metrics']['cost_usd_display'] == "0,001230 USD"


def test_session_local_backend_excludes_message_column(temp_hilt_file: Path):
    """Message column can be excluded for privacy."""
    columns_no_message = [
        'timestamp',
        'conversation_id',
        'speaker',
        'action',
        'tokens_in',
        'tokens_out',
        'cost_usd',
        'model'
    ]

    with Session(
        backend="local",
        filepath=temp_hilt_file,
        columns=columns_no_message
    ) as session:
        event = Event(
            session_id="sensitive_conv",
            actor=Actor(type="human", id="user"),
            action="prompt",
            content=Content(text="This is sensitive private data that should NOT be logged!"),
            metrics=Metrics(
                tokens={"prompt": 50, "completion": 100, "total": 150},
                cost_usd=0.00234
            ),
            extensions={"model": "gpt-4o-mini"}
        )
        session.append(event)

    data = json.loads(temp_hilt_file.read_text().splitlines()[0])

    assert 'message' not in data
    assert 'timestamp' in data
    assert 'speaker' in data
    assert 'action' in data
    assert 'cost_usd' in data
    assert data['cost_usd'] == "0.002340"
    assert data['model'] == "gpt-4o-mini"
    assert data['tokens_in'] == 50
    assert data['tokens_out'] == 100

    # Ensure no trace of message content anywhere
    assert "sensitive private data" not in temp_hilt_file.read_text().lower()


def test_session_local_backend_invalid_columns(temp_hilt_file: Path):
    """Invalid column names raise error."""
    with pytest.raises(ValueError, match="Invalid columns"):
        Session(
            backend="local",
            filepath=temp_hilt_file,
            columns=['timestamp', 'invalid_field', 'message']
        )


def test_session_local_backend_filtered_event_to_dict(temp_hilt_file: Path):
    """_event_to_filtered_dict returns only requested columns."""
    custom_columns = ['timestamp', 'speaker', 'action', 'message', 'cost_usd']

    with Session(
        backend="local",
        filepath=temp_hilt_file,
        columns=custom_columns
    ) as session:
        event = Event(
            session_id="test_conv",
            actor=Actor(type="agent", id="assistant"),
            action="completion",
            content=Content(text="Hello, how can I help you?"),
            metrics=Metrics(cost_usd=0.00156)
        )
        filtered = session._event_to_filtered_dict(event)

    assert set(filtered.keys()) == set(custom_columns)
    assert 'timestamp' in filtered
    assert filtered['speaker'] == "agent: assistant"
    assert filtered['action'] == "completion"
    assert filtered['message'] == "Hello, how can I help you?"
    assert filtered['cost_usd'] == "0.001560"


def test_session_local_backend_read_filtered_events(temp_hilt_file: Path):
    """Reading back filtered events reconstructs minimal Event objects."""
    custom_columns = ['timestamp', 'speaker', 'action', 'cost_usd']

    with Session(
        backend="local",
        filepath=temp_hilt_file,
        columns=custom_columns
    ) as session:
        for i in range(3):
            event = Event(
                session_id=f"conv_{i}",
                actor=Actor(type="human", id=f"user_{i}"),
                action="prompt",
                content=Content(text=f"Message {i}"),
                metrics=Metrics(cost_usd=0.001 * (i + 1))
            )
            session.append(event)

    read_session = Session(
        backend="local",
        filepath=temp_hilt_file,
        mode="r",
        columns=custom_columns
    )
    events = list(read_session.read())

    assert len(events) == 3
    assert events[0].actor.id == "user_0"
    assert events[1].actor.id == "user_1"
    assert events[2].actor.id == "user_2"


def test_session_local_backend_multiple_columns_combinations(temp_hilt_file: Path):
    """Various column combinations should work."""
    test_cases = [
        ['timestamp', 'action'],  # Minimal
        ['timestamp', 'speaker', 'action', 'cost_usd', 'model'],  # Metadata only
        ['timestamp', 'message', 'cost_usd'],  # With message
        ['timestamp', 'tokens_in', 'tokens_out', 'cost_usd', 'model'],  # Tokens & cost
    ]

    for columns in test_cases:
        if temp_hilt_file.exists():
            temp_hilt_file.unlink()

        with Session(
            backend="local",
            filepath=temp_hilt_file,
            columns=columns
        ) as session:
            event = Event(
                session_id="test",
                actor=Actor(type="human", id="user"),
                action="prompt",
                content=Content(text="Test message"),
                metrics=Metrics(
                    tokens={"prompt": 10, "completion": 20, "total": 30},
                    cost_usd=0.00123
                ),
                extensions={"model": "gpt-4o-mini"}
            )
            session.append(event)

        data = json.loads(temp_hilt_file.read_text().splitlines()[0])
        assert set(data.keys()) == set(columns), f"Failed for columns: {columns}"


def test_session_local_backend_long_message_truncation(temp_hilt_file: Path):
    """Long messages are truncated to 500 chars in filtered mode."""
    custom_columns = ['timestamp', 'message', 'action']

    with Session(
        backend="local",
        filepath=temp_hilt_file,
        columns=custom_columns
    ) as session:
        long_message = "A" * 600  # More than 500 chars
        event = Event(
            session_id="test",
            actor=Actor(type="human", id="user"),
            action="prompt",
            content=Content(text=long_message)
        )
        session.append(event)

    data = json.loads(temp_hilt_file.read_text().splitlines()[0])
    assert len(data['message']) == 500
    assert data['message'].endswith("...")


def test_session_local_backend_metrics_extraction(temp_hilt_file: Path):
    """Metrics (tokens + cost) correctly extracted into columns."""
    columns = ['timestamp', 'tokens_in', 'tokens_out', 'cost_usd']

    with Session(
        backend="local",
        filepath=temp_hilt_file,
        columns=columns
    ) as session:
        event = Event(
            session_id="test",
            actor=Actor(type="agent", id="assistant"),
            action="completion",
            metrics=Metrics(
                tokens={"prompt": 150, "completion": 300, "total": 450},
                cost_usd=0.005678
            )
        )
        session.append(event)

    data = json.loads(temp_hilt_file.read_text().splitlines()[0])
    assert data['tokens_in'] == 150
    assert data['tokens_out'] == 300
    assert data['cost_usd'] == "0.005678"


def test_session_local_backend_extensions_extraction(temp_hilt_file: Path):
    """Extensions (model, latency_ms, status_code, score->relevance_score) extracted."""
    columns = ['timestamp', 'model', 'latency_ms', 'status_code', 'relevance_score']

    with Session(
        backend="local",
        filepath=temp_hilt_file,
        columns=columns
    ) as session:
        event = Event(
            session_id="test",
            actor=Actor(type="agent", id="assistant"),
            action="completion",
            extensions={
                "model": "gpt-4o-mini",
                "latency_ms": 2500,
                "status_code": 200,
                "score": 0.95
            }
        )
        session.append(event)

    data = json.loads(temp_hilt_file.read_text().splitlines()[0])
    assert data['model'] == "gpt-4o-mini"
    assert data['latency_ms'] == 2500
    assert data['status_code'] == 200
    assert data['relevance_score'] == 0.95



# ============================================================================
# INTEGRATION-LIKE PARITY CHECK (no external services)
# ============================================================================

def test_session_local_vs_sheets_column_parity(temp_hilt_file: Path):
    """Local and sheets backends validate against the same ALL_COLUMNS list."""
    custom_columns = ['timestamp', 'speaker', 'action', 'cost_usd']

    # Local backend accepts the same columns set
    with Session(
        backend="local",
        filepath=temp_hilt_file,
        columns=custom_columns
    ) as session:
        assert session.columns == custom_columns
        assert session.backend == "local"

    # Validate exposed ALL_COLUMNS contains keys we rely on
        from hilt.io.session import ALL_COLUMNS
        assert 'timestamp' in ALL_COLUMNS
        assert 'speaker' in ALL_COLUMNS
        assert 'cost_usd' in ALL_COLUMNS

    # Invalid column should fail for both
    with pytest.raises(ValueError, match="Invalid columns"):
        Session(
            backend="local",
            filepath=temp_hilt_file,
            columns=['invalid_column']
        )
