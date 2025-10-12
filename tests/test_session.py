"""Tests for Session class with configurable columns."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from hilt import Session, Event, Actor, Content, HILTError


@pytest.fixture
def temp_hilt_file(tmp_path):
    """Create a temporary HILT file."""
    return tmp_path / "test.hilt.jsonl"


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


def test_session_backend_validation():
    """Test that invalid backend raises error."""
    with pytest.raises(ValueError, match="Invalid backend"):
        Session(backend="invalid")


def test_session_local_backend_requires_filepath():
    """Test that local backend requires filepath."""
    with pytest.raises(ValueError, match="filepath is required"):
        Session(backend="local")


@patch('google.oauth2.service_account.Credentials')
@patch('gspread.authorize')
def test_session_sheets_backend_default_columns(mock_authorize, mock_creds, tmp_path):
    """Test Google Sheets backend with default columns."""
    # Mock the gspread client
    mock_client = MagicMock()
    mock_spreadsheet = MagicMock()
    mock_worksheet = MagicMock()
    
    mock_authorize.return_value = mock_client
    mock_client.open_by_key.return_value = mock_spreadsheet
    mock_spreadsheet.worksheet.return_value = mock_worksheet
    mock_worksheet.row_values.return_value = []
    
    # Create session with sheets backend
    session = Session(
        backend="sheets",
        sheet_id="test-sheet-id",
        credentials_path=str(tmp_path / "creds.json")
    )
    
    # Verify all 14 columns are used by default
    assert len(session.columns) == 14
    assert session.columns[0] == 'timestamp'
    assert session.columns[3] == 'status_code'
    assert session.columns[-1] == 'relevance_score'


@patch('google.oauth2.service_account.Credentials')
@patch('gspread.authorize')
def test_session_sheets_backend_custom_columns(mock_authorize, mock_creds, tmp_path):
    """Test Google Sheets backend with custom columns."""
    # Mock the gspread client
    mock_client = MagicMock()
    mock_spreadsheet = MagicMock()
    mock_worksheet = MagicMock()
    
    mock_authorize.return_value = mock_client
    mock_client.open_by_key.return_value = mock_spreadsheet
    mock_spreadsheet.worksheet.return_value = mock_worksheet
    mock_worksheet.row_values.return_value = []
    
    # Create session with custom columns
    custom_columns = ['timestamp', 'message', 'cost_usd', 'status_code']
    session = Session(
        backend="sheets",
        sheet_id="test-sheet-id",
        credentials_path=str(tmp_path / "creds.json"),
        columns=custom_columns
    )
    
    # Verify custom columns are used
    assert session.columns == custom_columns
    assert len(session.columns) == 4


@patch('google.oauth2.service_account.Credentials')
@patch('gspread.authorize')
def test_session_sheets_backend_invalid_columns(mock_authorize, mock_creds, tmp_path):
    """Test that invalid columns raise error."""
    # Mock the gspread client
    mock_client = MagicMock()
    mock_authorize.return_value = mock_client
    
    # Try to create session with invalid columns
    with pytest.raises(ValueError, match="Invalid columns"):
        Session(
            backend="sheets",
            sheet_id="test-sheet-id",
            credentials_path=str(tmp_path / "creds.json"),
            columns=['timestamp', 'invalid_column', 'message']
        )


@patch('google.oauth2.service_account.Credentials')
@patch('gspread.authorize')
def test_session_sheets_event_to_row_all_columns(mock_authorize, mock_creds, tmp_path):
    """Test event to row conversion with all columns."""
    # Mock the gspread client
    mock_client = MagicMock()
    mock_spreadsheet = MagicMock()
    mock_worksheet = MagicMock()
    
    mock_authorize.return_value = mock_client
    mock_client.open_by_key.return_value = mock_spreadsheet
    mock_spreadsheet.worksheet.return_value = mock_worksheet
    mock_worksheet.row_values.return_value = []
    
    # Create session with all columns
    session = Session(
        backend="sheets",
        sheet_id="test-sheet-id",
        credentials_path=str(tmp_path / "creds.json")
    )
    
    # Create event with metrics and extensions
    from hilt import Metrics
    event = Event(
        session_id="conv_abc123",
        actor=Actor(type="agent", id="assistant"),
        action="completion",
        content=Content(text="Test answer"),
        metrics=Metrics(
            tokens={"prompt": 10, "completion": 20, "total": 30},
            cost_usd=0.00045
        ),
        extensions={
            "status_code": 200,
            "model": "gpt-4o-mini",
            "latency_ms": 1500,
            "score": 0.85
        }
    )
    
    # Convert to row
    row = session._event_to_sheet_row(event)
    
    # Verify row has 14 values (all columns)
    assert len(row) == 14
    
    # Verify specific values
    assert row[3] == 200  # status_code
    assert row[8] == 10  # tokens_in
    assert row[9] == 20  # tokens_out
    assert row[10] == 0.00045  # cost_usd
    assert row[11] == 1500  # latency_ms
    assert row[12] == "gpt-4o-mini"  # model
    assert row[13] == 0.85  # relevance_score


@patch('google.oauth2.service_account.Credentials')
@patch('gspread.authorize')
def test_session_sheets_event_to_row_custom_columns(mock_authorize, mock_creds, tmp_path):
    """Test event to row conversion with custom columns."""
    # Mock the gspread client
    mock_client = MagicMock()
    mock_spreadsheet = MagicMock()
    mock_worksheet = MagicMock()
    
    mock_authorize.return_value = mock_client
    mock_client.open_by_key.return_value = mock_spreadsheet
    mock_spreadsheet.worksheet.return_value = mock_worksheet
    mock_worksheet.row_values.return_value = []
    
    # Create session with only 4 columns
    custom_columns = ['timestamp', 'message', 'cost_usd', 'status_code']
    session = Session(
        backend="sheets",
        sheet_id="test-sheet-id",
        credentials_path=str(tmp_path / "creds.json"),
        columns=custom_columns
    )
    
    # Create event
    from hilt import Metrics
    event = Event(
        session_id="conv_abc123",
        actor=Actor(type="agent", id="assistant"),
        action="completion",
        content=Content(text="Test answer"),
        metrics=Metrics(cost_usd=0.00045),
        extensions={"status_code": 200}
    )
    
    # Convert to row
    row = session._event_to_sheet_row(event)
    
    # Verify row has only 4 values (custom columns)
    assert len(row) == 4
    
    # Verify order matches custom_columns
    # [timestamp, message, cost_usd, status_code]
    assert row[1] == "Test answer"  # message
    assert row[2] == 0.00045  # cost_usd
    assert row[3] == 200  # status_code


@patch('google.oauth2.service_account.Credentials')
@patch('gspread.authorize')
def test_session_sheets_headers_with_custom_columns(mock_authorize, mock_creds, tmp_path):
    """Test that headers match custom columns."""
    # Mock the gspread client
    mock_client = MagicMock()
    mock_spreadsheet = MagicMock()
    mock_worksheet = MagicMock()
    
    mock_authorize.return_value = mock_client
    mock_client.open_by_key.return_value = mock_spreadsheet
    mock_spreadsheet.worksheet.return_value = mock_worksheet
    mock_worksheet.row_values.return_value = []
    
    # Create session with custom columns
    custom_columns = ['timestamp', 'speaker', 'message', 'status_code']
    session = Session(
        backend="sheets",
        sheet_id="test-sheet-id",
        credentials_path=str(tmp_path / "creds.json"),
        columns=custom_columns
    )
    
    # Verify append_row was called with custom headers
    mock_worksheet.append_row.assert_called_once()
    call_args = mock_worksheet.append_row.call_args[0][0]
    assert call_args == custom_columns


def test_session_local_backend_ignores_columns(temp_hilt_file):
    """Test that local backend ignores columns parameter."""
    # Create session with columns parameter (should be ignored for local)
    session = Session(
        backend="local",
        filepath=temp_hilt_file,
        columns=['timestamp', 'message']  # This should be ignored
    )
    
    # Verify columns is None for local backend
    assert session.columns is None
    
    # Verify session works normally
    with session:
        event = Event(
            session_id="test",
            actor=Actor(type="human", id="user"),
            action="prompt"
        )
        session.append(event)
    
    assert temp_hilt_file.exists()