"""Session manager for reading/writing HILT events."""

import json
import os
import re
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING, Any, TextIO, cast

from hilt.core.event import Event
from hilt.core.exceptions import HILTError
from hilt.utils.timestamp import get_utc_timestamp

if TYPE_CHECKING:  # pragma: no cover - import-time typing hints
    import gspread  # type: ignore[import-not-found]
    from google.oauth2.service_account import Credentials  # type: ignore[import-not-found]

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
    formatted = _format_cost_number(value)
    if formatted is None:
        return None
    return formatted.replace(".", ",") + " USD"


def _col_to_a1(col_index_1based: int) -> str:
    """Convert 1-based column index to A1 notation (A, B, ..., Z, AA, AB, ...)."""
    letters = []
    n = col_index_1based
    while n > 0:
        n, rem = divmod(n - 1, 26)
        letters.append(chr(65 + rem))
    return "".join(reversed(letters))


def _stringify(value: Any) -> str:
    """Convert arbitrary values to the string representation expected by Sheets/output."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _parse_timestamp(value: Any) -> datetime:
    """Best-effort conversion of timestamp fields back to datetime."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        candidate = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            pass
    return get_utc_timestamp()


def _event_column_values(event: Event) -> dict[str, Any]:
    """Extract flattened column values from an event."""
    actor_type = event.actor.type
    actor_id = event.actor.id
    speaker = f"{actor_type}: {actor_id}"

    # Format timestamp
    if hasattr(event.timestamp, "strftime"):
        timestamp_str = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    else:
        timestamp_str = str(event.timestamp)

    conversation_id = event.session_id
    event_id = event.event_id

    # Session short display
    if conversation_id.startswith("conv_"):
        session_display: str = f"Conv.{conversation_id[5:13]}"
    elif conversation_id.startswith("rag_chat_"):
        session_display = conversation_id.replace("rag_chat_", "Conv.")
    else:
        session_display = conversation_id[:12]

    # Message content (sanitize newlines/length)
    raw_message = (event.content.text if event.content else "") or ""
    message = raw_message.replace("\n", " ")
    message = re.sub(r"\s+", " ", message).strip()
    if len(message) > 500:
        message = message[:497] + "..."

    # Metrics
    tokens_in: Any = ""
    tokens_out: Any = ""
    cost_usd = ""
    if event.metrics:
        tokens_dict = getattr(event.metrics, "tokens", None)
        if isinstance(tokens_dict, dict):
            if "prompt" in tokens_dict:
                prompt_val = tokens_dict["prompt"]
                tokens_in = prompt_val
            if "completion" in tokens_dict:
                completion_val = tokens_dict["completion"]
                tokens_out = completion_val

        cost_val = getattr(event.metrics, "cost_usd", None)
        if isinstance(cost_val, (int, float)):
            formatted = _format_cost_number(float(cost_val))
            if formatted is not None:
                cost_usd = formatted

    # Extensions
    extensions = event.extensions or {}
    reply_to = extensions.get("reply_to")
    if reply_to is None:
        reply_to = ""
    status_code = extensions.get("status_code", "")
    latency_ms = extensions.get("latency_ms", "")
    model = extensions.get("model", "")
    relevance_score = extensions.get("score", extensions.get("relevance_score", ""))

    return {
        "timestamp": timestamp_str,
        "conversation_id": conversation_id,
        "event_id": event_id,
        "reply_to": reply_to,
        "status_code": status_code,
        "session": session_display,
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
        credentials_json: dict[str, Any] | None = None,
        worksheet_name: str = "Logs",
        # Column filtering (now available for both backends)
        columns: list[str] | None = None,
    ):
        """Initialize Session with local or Google Sheets backend."""

        self.filepath: Path | None = None
        self.columns: list[str] | None = None
        self.sheets_client: Any | None = None
        self.spreadsheet: Any | None = None
        self.sheet_id: str | None = None
        self.worksheet: Any | None = None
        self.mode: str = mode
        self.encoding: str = encoding
        self._file_handle: TextIO | None = None
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
            selected_columns = list(columns)
            # Validate columns
            invalid_cols = [col for col in selected_columns if col not in ALL_COLUMNS]
            if invalid_cols:
                raise ValueError(
                    f"Invalid columns: {invalid_cols}. " f"Available columns: {ALL_COLUMNS}"
                )
            self.columns = selected_columns
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

    def _require_columns(self) -> list[str]:
        """Return configured columns or raise if they are missing."""
        if self.columns is None:
            raise HILTError("Column filtering requested but no columns are configured.")
        return self.columns

    def _require_worksheet(self) -> Any:
        """Return the worksheet or raise if the sheets backend is not initialized."""
        if self.worksheet is None:
            raise HILTError("Google Sheets worksheet is not initialized.")
        return self.worksheet

    def _init_local_backend(
        self, filepath: str | Path | None, mode: str, create_dirs: bool, encoding: str
    ) -> None:
        """Initialize local file backend."""
        if filepath is None:
            raise ValueError("filepath is required for backend='local'")

        self.filepath = Path(filepath)
        self.mode = mode
        self.encoding = encoding
        self._file_handle = None

        if create_dirs and mode in ("a", "w"):
            self.filepath.parent.mkdir(parents=True, exist_ok=True)

    def _init_sheets_backend(
        self,
        sheet_id: str | None,
        credentials_path: str | None,
        credentials_json: dict[str, Any] | None,
        worksheet_name: str,
    ) -> None:
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
            import gspread  # type: ignore[import-not-found]
            from google.oauth2.service_account import Credentials  # type: ignore[import-not-found]
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
            spreadsheet = self.sheets_client.open_by_key(sheet_id)
        except gspread.exceptions.SpreadsheetNotFound:
            raise ValueError(
                f"Google Spreadsheet with ID '{sheet_id}' not found. "
                "Make sure the sheet exists and is shared with your service account."
            )
        self.spreadsheet = spreadsheet

        self.worksheet_name = worksheet_name

        # Get or create worksheet
        try:
            self.worksheet = spreadsheet.worksheet(worksheet_name)
            print(f"   ✅ Worksheet '{worksheet_name}' found")
        except gspread.exceptions.WorksheetNotFound:
            print(f"   ⚠️  Worksheet '{worksheet_name}' not found, creating...")
            try:
                columns = self._require_columns()
                self.worksheet = spreadsheet.add_worksheet(
                    title=worksheet_name, rows=1000, cols=len(columns)
                )
                print(f"   ✅ Worksheet '{worksheet_name}' created successfully!")
            except Exception as e:
                raise HILTError(f"Failed to create worksheet '{worksheet_name}': {e}") from e

        # Ensure headers
        self._ensure_sheet_headers()

        # Store filepath as None for sheets backend
        self.filepath = None

    def _ensure_sheet_headers(self) -> None:
        """Ensure Google Sheet has proper headers based on selected columns."""
        if self.columns is None:
            return
        worksheet = self._require_worksheet()
        headers = self._require_columns()

        try:
            all_values = worksheet.get_all_values()

            if not all_values:
                worksheet.update("A1", [headers])
                print("   ✅ Headers added to Google Sheets")
            elif not all_values[0] or all_values[0] != headers:
                end_col = _col_to_a1(len(headers))
                range_name = f"A1:{end_col}1"
                worksheet.update(range_name, [headers])
                print("   ✅ Headers updated in Google Sheets")
            else:
                print("   ✅ Headers already correct")

            # Optional: Format headers (bold + background)
            try:
                end_col = _col_to_a1(len(headers))
                worksheet.format(
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
                worksheet.update("A1", [headers])
                print("   ✅ Headers added (fallback method)")
            except Exception as e2:
                print(f"   ⚠️  Unable to add headers: {e2}")

    def __enter__(self) -> "Session":
        """Context manager entry."""
        if self.backend == "local":
            if self.filepath is None:
                raise HILTError("Session filepath is not set for local backend.")
            self._file_handle = cast(TextIO, open(self.filepath, self.mode, encoding=self.encoding))
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Context manager exit."""
        self.close()

    def open(self) -> None:
        """Open the file explicitly (alternative to context manager)."""
        if self.backend == "local" and self._file_handle is None:
            if self.filepath is None:
                raise HILTError("Session filepath is not set for local backend.")
            self._file_handle = cast(TextIO, open(self.filepath, self.mode, encoding=self.encoding))

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

    def _event_to_filtered_dict(self, event: Event) -> dict[str, Any]:
        """Convert Event to filtered dictionary with only selected columns."""
        columns = self._require_columns()
        values = _event_column_values(event)
        return {col: values.get(col, "") for col in columns}

    def _append_to_sheets(self, event: Event) -> None:
        """
        Append event to Google Sheets immediately (real-time).

        This implementation writes each event directly to Google Sheets
        without buffering, enabling real-time data visibility.
        """
        try:
            worksheet = self._require_worksheet()
            row = self._event_to_sheet_row(event)
            worksheet.append_row(row, value_input_option="USER_ENTERED")
        except Exception as e:
            raise HILTError(f"Failed to write to Google Sheets: {e}") from e

    def _event_to_sheet_row(self, event: Event) -> list[str]:
        """Convert Event to Google Sheets row with only selected columns."""
        columns = self._require_columns()
        values = _event_column_values(event)
        return [_stringify(values.get(col, "")) for col in columns]

    def read(self) -> Iterator[Event]:
        """Read all events from the backend."""
        if self.backend == "local":
            yield from self._read_from_file()
        elif self.backend == "sheets":
            yield from self._read_from_sheets()

    def _read_from_file(self) -> Iterator[Event]:
        """Read events from local file."""
        if self.filepath is None:
            raise HILTError("Session filepath is not set for local backend.")
        path = self.filepath
        if not path.exists():
            raise HILTError(f"File not found: {path}")

        with path.open(encoding=self.encoding) as f:
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

    def _filtered_dict_to_event(self, data: dict[str, Any]) -> Event:
        """Reconstruct Event from filtered dictionary."""
        from hilt.core.actor import Actor
        from hilt.core.event import Content

        # Parse speaker if available
        speaker_str = _stringify(data.get("speaker", "unknown: unknown"))
        parts = speaker_str.split(":", 1)
        actor_type = parts[0].strip() if len(parts) > 1 else "unknown"
        actor_id = parts[1].strip() if len(parts) > 1 else speaker_str

        # Create minimal Event
        timestamp_value: datetime = _parse_timestamp(data.get("timestamp", ""))
        event = Event(
            session_id=_stringify(data.get("conversation_id", "unknown")),
            actor=Actor(type=actor_type, id=actor_id),
            action=_stringify(data.get("action", "unknown")),
            content=Content(text=_stringify(data.get("message", ""))),
            timestamp=timestamp_value,
        )

        # Add available extensions
        extensions: dict[str, str] = {}
        if "reply_to" in data and data["reply_to"]:
            extensions["reply_to"] = _stringify(data["reply_to"])
        if "status_code" in data and data["status_code"]:
            extensions["status_code"] = _stringify(data["status_code"])
        if "latency_ms" in data and data["latency_ms"]:
            extensions["latency_ms"] = _stringify(data["latency_ms"])
        if "model" in data and data["model"]:
            extensions["model"] = _stringify(data["model"])
        if "relevance_score" in data and data["relevance_score"]:
            extensions["relevance_score"] = _stringify(data["relevance_score"])

        if extensions:
            event.extensions = extensions

        return event

    def _read_from_sheets(self) -> Iterator[Event]:
        """Read events from Google Sheets."""
        try:
            worksheet = self._require_worksheet()
            records: list[dict[str, Any]] = worksheet.get_all_records()

            for record in records:
                # Parse speaker
                speaker_str = _stringify(record.get("speaker", ""))
                parts = speaker_str.split(":", 1)
                actor_type = parts[0].strip() if len(parts) > 1 else "unknown"
                actor_id = parts[1].strip() if len(parts) > 1 else speaker_str

                # Create Event (prefer conversation_id if present)
                from hilt.core.actor import Actor
                from hilt.core.event import Content

                session_id_value = record.get("conversation_id")
                if not session_id_value:
                    session_id_value = record.get("session", "unknown")
                session_id = _stringify(session_id_value)
                timestamp_value: datetime = _parse_timestamp(record.get("timestamp", ""))
                event = Event(
                    session_id=session_id,
                    actor=Actor(type=actor_type, id=actor_id),
                    action=_stringify(record.get("action", "unknown")),
                    content=Content(text=_stringify(record.get("message", ""))),
                    timestamp=timestamp_value,
                )

                # Reinstate extensions
                ex: dict[str, str] = {}
                if record.get("reply_to"):
                    ex["reply_to"] = _stringify(record["reply_to"])
                if record.get("status_code"):
                    ex["status_code"] = _stringify(record["status_code"])
                if record.get("latency_ms"):
                    ex["latency_ms"] = _stringify(record["latency_ms"])
                if record.get("model"):
                    ex["model"] = _stringify(record["model"])
                if record.get("relevance_score"):
                    ex["relevance_score"] = _stringify(record["relevance_score"])
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
