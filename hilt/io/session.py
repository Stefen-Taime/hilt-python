"""Session manager for reading/writing HILT events."""

import json
import os
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from hilt.core.event import Event
from hilt.core.exceptions import HILTError

# All available columns for Google Sheets and local filtering
ALL_COLUMNS = [
    "timestamp",
    "conversation_id",
    "event_id",
    "reply_to",
    "status_code",
    "session",
    "speaker",
    "action",
    "message",
    "tokens_in",
    "tokens_out",
    "cost_usd",
    "latency_ms",
    "model",
    "relevance_score",
]


def _format_cost_number(value: float | None) -> str | None:
    """Format cost with six decimals (dot separator)."""
    if value is None:
        return None
    return f"{value:.6f}"


def _format_cost_display(value: float | None) -> str | None:
    """Format cost as localized string with currency (e.g., 0,000065 USD)."""
    if value is None:
        return None
    return _format_cost_number(value).replace(".", ",") + " USD"


def _col_to_a1(col_index_1based: int) -> str:
    """Convert 1-based column index to A1 notation (A, B, ..., Z, AA, AB, ...)."""
    letters = []
    n = col_index_1based
    while n > 0:
        n, rem = divmod(n - 1, 26)
        letters.append(chr(65 + rem))
    return "".join(reversed(letters))


class Session:
    """
    HILT session manager for reading/writing events.

    Supports two backends:
    1. Local file (.jsonl) - default
    2. Google Sheets - for real-time collaboration with metrics tracking

    Attributes:
        backend: 'local' or 'sheets'
        filepath: Path to JSONL file (for local backend)
        columns: List of columns to display (for both backends)
    """

    def __init__(
        self,
        backend_or_filepath: str | Path | None = None,
        # Local backend parameters
        filepath: str | Path | None = None,
        mode: str = "a",
        create_dirs: bool = True,
        encoding: str = "utf-8",
        # Explicit backend parameter
        backend: str | None = None,
        # Google Sheets backend parameters
        sheet_id: str | None = None,
        credentials_path: str | None = None,
        credentials_json: dict | None = None,
        worksheet_name: str = "Logs",
        # Column filtering (now available for both backends)
        columns: list[str] | None = None,
    ):
        """Initialize Session with local or Google Sheets backend."""

        # Determine backend and filepath from arguments
        resolved_backend = backend
        resolved_filepath = filepath

        # Handle first argument - could be backend name or filepath
        if backend_or_filepath is not None:
            backend_str = str(backend_or_filepath)
            if backend_str in ("local", "sheets"):
                resolved_backend = backend_str
            else:
                resolved_backend = "local"
                resolved_filepath = backend_or_filepath

        # Default to local backend if not specified
        if resolved_backend is None:
            resolved_backend = "local"

        # Validate backend
        if resolved_backend not in ("local", "sheets"):
            raise ValueError(f"Invalid backend '{resolved_backend}'. Must be 'local' or 'sheets'.")

        self.backend = resolved_backend

        # Set and validate columns for both backends
        if columns is not None:
            self.columns = columns
            # Validate columns
            invalid_cols = [col for col in self.columns if col not in ALL_COLUMNS]
            if invalid_cols:
                raise ValueError(
                    f"Invalid columns: {invalid_cols}. " f"Available columns: {ALL_COLUMNS}"
                )
        else:
            # Default to all columns for sheets, None for local (no filtering)
            if self.backend == "sheets":
                self.columns = ALL_COLUMNS.copy()
            else:
                self.columns = None

        # Initialize based on backend
        if self.backend == "local":
            self._init_local_backend(resolved_filepath, mode, create_dirs, encoding)
        elif self.backend == "sheets":
            self._init_sheets_backend(sheet_id, credentials_path, credentials_json, worksheet_name)

    def _init_local_backend(
        self, filepath: str | Path | None, mode: str, create_dirs: bool, encoding: str
    ):
        """Initialize local file backend."""
        if filepath is None:
            raise ValueError("filepath is required for backend='local'")

        self.filepath = Path(filepath)
        self.mode = mode
        self.encoding = encoding
        self._file_handle: Any | None = None

        if create_dirs and mode in ("a", "w"):
            self.filepath.parent.mkdir(parents=True, exist_ok=True)

    def _init_sheets_backend(
        self,
        sheet_id: str | None,
        credentials_path: str | None,
        credentials_json: dict | None,
        worksheet_name: str,
    ):
        """Initialize Google Sheets backend."""
        if sheet_id is None:
            sheet_id = os.getenv("GOOGLE_SHEET_ID")

        if not sheet_id:
            raise ValueError(
                "sheet_id is required for backend='sheets'. "
                "Provide it as parameter or set GOOGLE_SHEET_ID environment variable."
            )

        # Import Google Sheets dependencies
        try:
            import gspread
            from google.oauth2.service_account import Credentials
        except ImportError:
            raise ImportError(
                "Google Sheets backend requires additional dependencies. "
                "Install with: pip install hilt[sheets]"
            )

        # Get credentials
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        if credentials_json:
            creds = Credentials.from_service_account_info(credentials_json, scopes=scopes)
        elif credentials_path:
            creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
        else:
            creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
            if creds_path:
                creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
            else:
                raise ValueError(
                    "credentials_path or credentials_json is required for backend='sheets'. "
                    "Provide it as parameter or set GOOGLE_CREDENTIALS_PATH environment variable."
                )

        # Initialize client
        self.sheets_client = gspread.authorize(creds)
        self.sheet_id = sheet_id

        try:
            self.spreadsheet = self.sheets_client.open_by_key(sheet_id)
        except gspread.exceptions.SpreadsheetNotFound:
            raise ValueError(
                f"Google Spreadsheet with ID '{sheet_id}' not found. "
                "Make sure the sheet exists and is shared with your service account."
            )

        self.worksheet_name = worksheet_name

        # Get or create worksheet
        try:
            self.worksheet = self.spreadsheet.worksheet(worksheet_name)
            print(f"   ✅ Worksheet '{worksheet_name}' found")
        except gspread.exceptions.WorksheetNotFound:
            print(f"   ⚠️  Worksheet '{worksheet_name}' not found, creating...")
            try:
                num_cols = len(self.columns)
                self.worksheet = self.spreadsheet.add_worksheet(
                    title=worksheet_name, rows=1000, cols=num_cols
                )
                print(f"   ✅ Worksheet '{worksheet_name}' created successfully!")
            except Exception as e:
                raise HILTError(f"Failed to create worksheet '{worksheet_name}': {e}") from e

        # Ensure headers
        self._ensure_sheet_headers()

        # Store filepath as None for sheets backend
        self.filepath = None

    def _ensure_sheet_headers(self):
        """Ensure Google Sheet has proper headers based on selected columns."""
        headers = self.columns

        try:
            all_values = self.worksheet.get_all_values()

            if not all_values:
                self.worksheet.update("A1", [headers])
                print("   ✅ Headers added to Google Sheets")
            elif not all_values[0] or all_values[0] != headers:
                end_col = _col_to_a1(len(headers))
                range_name = f"A1:{end_col}1"
                self.worksheet.update(range_name, [headers])
                print("   ✅ Headers updated in Google Sheets")
            else:
                print("   ✅ Headers already correct")

            # Optional: Format headers (bold + background)
            try:
                end_col = _col_to_a1(len(headers))
                self.worksheet.format(
                    f"A1:{end_col}1",
                    {
                        "textFormat": {"bold": True},
                        "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
                    },
                )
            except Exception:
                pass

        except Exception:
            try:
                self.worksheet.update("A1", [headers])
                print("   ✅ Headers added (fallback method)")
            except Exception as e2:
                print(f"   ⚠️  Unable to add headers: {e2}")

    def __enter__(self) -> "Session":
        """Context manager entry."""
        if self.backend == "local":
            self._file_handle = open(self.filepath, self.mode, encoding=self.encoding)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def open(self) -> None:
        """Open the file explicitly (alternative to context manager)."""
        if self.backend == "local" and self._file_handle is None:
            self._file_handle = open(self.filepath, self.mode, encoding=self.encoding)

    def append(self, event: Event) -> None:
        """Append an event to the backend."""
        if self.backend == "local":
            self._append_to_file(event)
        elif self.backend == "sheets":
            self._append_to_sheets(event)

    def _append_to_file(self, event: Event) -> None:
        """Append event to local file with optional column filtering."""
        if self._file_handle is None:
            raise HILTError("Session not opened. Use context manager or call open().")

        try:
            if self.columns is None:
                # No filtering - write full event as JSON with formatted cost display
                data = event.to_dict()
                metrics = data.get("metrics")
                if isinstance(metrics, dict):
                    raw_cost = metrics.get("cost_usd")
                    formatted = (
                        _format_cost_number(raw_cost)
                        if isinstance(raw_cost, (int, float))
                        else None
                    )
                    display = (
                        _format_cost_display(raw_cost)
                        if isinstance(raw_cost, (int, float))
                        else None
                    )
                    if formatted is not None:
                        metrics["cost_usd"] = formatted
                    if display:
                        metrics["cost_usd_display"] = display
                json_line = json.dumps(data, ensure_ascii=False)
            else:
                # Filter event data to include only specified columns
                filtered_data = self._event_to_filtered_dict(event)
                json_line = json.dumps(filtered_data, ensure_ascii=False)

            self._file_handle.write(json_line + "\n")
            self._file_handle.flush()
        except Exception as e:
            raise HILTError(f"Failed to write event: {e}") from e

    def _event_to_filtered_dict(self, event: Event) -> dict:
        """Convert Event to filtered dictionary with only selected columns."""

        # Extract basic fields
        actor_type = event.actor.type
        actor_id = event.actor.id
        speaker = f"{actor_type}: {actor_id}"

        # Format timestamp
        if hasattr(event.timestamp, "strftime"):
            timestamp_str = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        else:
            timestamp_str = str(event.timestamp)

        # Get conversation_id
        conversation_id = event.session_id

        # Get event_id
        event_id = event.event_id

        # Get reply_to from extensions
        reply_to = ""
        if event.extensions:
            reply_to = event.extensions.get("reply_to", "")

        # Get status_code from extensions
        status_code = ""
        if event.extensions:
            status_code = event.extensions.get("status_code", "")

        # Get session (short display)
        if conversation_id.startswith("conv_"):
            session = f"Conv.{conversation_id[5:13]}"
        elif conversation_id.startswith("rag_chat_"):
            session = conversation_id.replace("rag_chat_", "Conv.")
        else:
            session = conversation_id[:12]

        # Get message text
        message = event.content.text if event.content else ""
        message = message.replace("\n", " ")
        message = re.sub(r"\s+", " ", message).strip()
        if len(message) > 500:
            message = message[:497] + "..."

        # Extract metrics
        tokens_in = ""
        tokens_out = ""
        cost_usd = ""

        if event.metrics:
            if hasattr(event.metrics, "tokens") and event.metrics.tokens:
                tokens_dict = event.metrics.tokens
                if isinstance(tokens_dict, dict):
                    tokens_in = tokens_dict.get("prompt", "")
                    tokens_out = tokens_dict.get("completion", "")

            if hasattr(event.metrics, "cost_usd") and event.metrics.cost_usd is not None:
                formatted = _format_cost_number(event.metrics.cost_usd)
                if formatted is not None:
                    cost_usd = formatted

        # Extract extensions
        latency_ms = ""
        model = ""
        relevance_score = ""

        if event.extensions:
            latency_ms = event.extensions.get("latency_ms", "")
            model = event.extensions.get("model", "")
            relevance_score = event.extensions.get("score", "") or event.extensions.get(
                "relevance_score", ""
            )

        # Map all possible column values
        all_values = {
            "timestamp": timestamp_str,
            "conversation_id": conversation_id,
            "event_id": event_id,
            "reply_to": reply_to,
            "status_code": status_code,
            "session": session,
            "speaker": speaker,
            "action": event.action,
            "message": message,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": cost_usd,
            "latency_ms": latency_ms,
            "model": model,
            "relevance_score": relevance_score,
        }

        # Return only selected columns
        return {col: all_values.get(col, "") for col in self.columns}

    def _append_to_sheets(self, event: Event) -> None:
        """
        Append event to Google Sheets immediately (real-time).

        This implementation writes each event directly to Google Sheets
        without buffering, enabling real-time data visibility.
        """
        try:
            row = self._event_to_sheet_row(event)
            self.worksheet.append_row(row, value_input_option="USER_ENTERED")
        except Exception as e:
            raise HILTError(f"Failed to write to Google Sheets: {e}") from e

    def _event_to_sheet_row(self, event: Event) -> list:
        """Convert Event to Google Sheets row with only selected columns."""

        # Extract basic fields
        actor_type = event.actor.type
        actor_id = event.actor.id
        speaker = f"{actor_type}: {actor_id}"

        # Format timestamp
        if hasattr(event.timestamp, "strftime"):
            timestamp_str = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        else:
            timestamp_str = str(event.timestamp)

        # Get conversation_id
        conversation_id = event.session_id

        # Get event_id
        event_id = event.event_id

        # Get reply_to from extensions
        reply_to = ""
        if event.extensions:
            reply_to = event.extensions.get("reply_to", "")

        # Get status_code from extensions
        status_code = ""
        if event.extensions:
            status_code = event.extensions.get("status_code", "")

        # Get session (short display)
        if conversation_id.startswith("conv_"):
            session = f"Conv.{conversation_id[5:13]}"
        elif conversation_id.startswith("rag_chat_"):
            session = conversation_id.replace("rag_chat_", "Conv.")
        else:
            session = conversation_id[:12]

        # Get message text
        message = event.content.text if event.content else ""
        message = message.replace("\n", " ")
        message = re.sub(r"\s+", " ", message).strip()
        if len(message) > 500:
            message = message[:497] + "..."

        # Extract metrics
        tokens_in = ""
        tokens_out = ""
        cost_usd = ""

        if event.metrics:
            if hasattr(event.metrics, "tokens") and event.metrics.tokens:
                tokens_dict = event.metrics.tokens
                if isinstance(tokens_dict, dict):
                    tokens_in = tokens_dict.get("prompt", "")
                    tokens_out = tokens_dict.get("completion", "")

            if hasattr(event.metrics, "cost_usd") and event.metrics.cost_usd is not None:
                formatted = _format_cost_number(event.metrics.cost_usd)
                if formatted is not None:
                    cost_usd = formatted

        # Extract extensions
        latency_ms = ""
        model = ""
        relevance_score = ""

        if event.extensions:
            latency_ms = event.extensions.get("latency_ms", "")
            model = event.extensions.get("model", "")
            relevance_score = event.extensions.get("score", "") or event.extensions.get(
                "relevance_score", ""
            )

        # Map all possible column values
        all_values = {
            "timestamp": timestamp_str,
            "conversation_id": conversation_id,
            "event_id": event_id,
            "reply_to": reply_to,
            "status_code": status_code,
            "session": session,
            "speaker": speaker,
            "action": event.action,
            "message": message,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": cost_usd,
            "latency_ms": latency_ms,
            "model": model,
            "relevance_score": relevance_score,
        }

        # Return only selected columns in the order specified by self.columns
        return [all_values.get(col, "") for col in self.columns]

    def read(self) -> Iterator[Event]:
        """Read all events from the backend."""
        if self.backend == "local":
            yield from self._read_from_file()
        elif self.backend == "sheets":
            yield from self._read_from_sheets()

    def _read_from_file(self) -> Iterator[Event]:
        """Read events from local file."""
        if not self.filepath.exists():
            raise HILTError(f"File not found: {self.filepath}")

        with open(self.filepath, encoding=self.encoding) as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue

                try:
                    if self.columns is None:
                        # Full event format
                        event = Event.from_json(line)
                    else:
                        # Filtered format - reconstruct minimal event
                        data = json.loads(line)
                        event = self._filtered_dict_to_event(data)
                    yield event
                except Exception as e:
                    raise HILTError(f"Invalid event at line {line_num}: {e}") from e

    def _filtered_dict_to_event(self, data: dict) -> Event:
        """Reconstruct Event from filtered dictionary."""
        from hilt.core.actor import Actor
        from hilt.core.event import Content

        # Parse speaker if available
        speaker_str = data.get("speaker", "unknown: unknown")
        parts = speaker_str.split(":", 1)
        actor_type = parts[0].strip() if len(parts) > 1 else "unknown"
        actor_id = parts[1].strip() if len(parts) > 1 else speaker_str

        # Create minimal Event
        event = Event(
            session_id=data.get("conversation_id", "unknown"),
            actor=Actor(type=actor_type, id=actor_id),
            action=data.get("action", "unknown"),
            content=Content(text=data.get("message", "")),
            timestamp=data.get("timestamp", ""),
        )

        # Add available extensions
        extensions = {}
        if "reply_to" in data and data["reply_to"]:
            extensions["reply_to"] = data["reply_to"]
        if "status_code" in data and data["status_code"]:
            extensions["status_code"] = data["status_code"]
        if "latency_ms" in data and data["latency_ms"]:
            extensions["latency_ms"] = data["latency_ms"]
        if "model" in data and data["model"]:
            extensions["model"] = data["model"]
        if "relevance_score" in data and data["relevance_score"]:
            extensions["relevance_score"] = data["relevance_score"]

        if extensions:
            event.extensions = extensions

        return event

    def _read_from_sheets(self) -> Iterator[Event]:
        """Read events from Google Sheets."""
        try:
            records = self.worksheet.get_all_records()

            for record in records:
                # Parse speaker
                speaker_str = record.get("speaker", "")
                parts = speaker_str.split(":", 1)
                actor_type = parts[0].strip() if len(parts) > 1 else "unknown"
                actor_id = parts[1].strip() if len(parts) > 1 else speaker_str

                # Create Event (prefer conversation_id if present)
                from hilt.core.actor import Actor
                from hilt.core.event import Content

                session_id = record.get("conversation_id") or record.get("session", "unknown")
                event = Event(
                    session_id=session_id,
                    actor=Actor(type=actor_type, id=actor_id),
                    action=record.get("action", "unknown"),
                    content=Content(text=record.get("message", "")),
                    timestamp=record.get("timestamp", ""),
                )

                # Reinstate extensions
                ex = {}
                if record.get("reply_to"):
                    ex["reply_to"] = record["reply_to"]
                if record.get("status_code"):
                    ex["status_code"] = record["status_code"]
                if record.get("latency_ms"):
                    ex["latency_ms"] = record["latency_ms"]
                if record.get("model"):
                    ex["model"] = record["model"]
                if record.get("relevance_score"):
                    ex["relevance_score"] = record["relevance_score"]
                if ex:
                    event.extensions = ex

                yield event
        except Exception as e:
            raise HILTError(f"Error reading from Google Sheets: {e}") from e

    def close(self) -> None:
        """Close the session and flush any pending data."""
        if self.backend == "local" and self._file_handle is not None:
            self._file_handle.close()
            self._file_handle = None


__all__ = ["Session"]
