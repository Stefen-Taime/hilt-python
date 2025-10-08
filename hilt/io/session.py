"""Session manager for reading/writing HILT events."""

from pathlib import Path
from typing import Iterator, Optional, Any

from hilt.core.event import Event
from hilt.core.exceptions import HILTError


class Session:
    """
    HILT session manager for reading/writing events.

    Attributes:
        filepath: Path to JSONL file
        mode: Open mode ('a' = append, 'w' = write, 'r' = read)

    Example:
        >>> with Session("logs/app.hilt.jsonl") as session:
        ...     session.append(Event(...))
        ...     session.append(Event(...))
    """

    def __init__(
        self,
        filepath: str | Path,
        mode: str = "a",
        create_dirs: bool = True,
        encoding: str = "utf-8",
    ):
        self.filepath = Path(filepath)
        self.mode = mode
        self.encoding = encoding
        self._file_handle: Optional[Any] = None

        if create_dirs and mode in ("a", "w"):
            self.filepath.parent.mkdir(parents=True, exist_ok=True)

    def __enter__(self) -> "Session":
        """Context manager entry."""
        self._file_handle = open(self.filepath, self.mode, encoding=self.encoding)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def open(self) -> None:
        """Open the file explicitly (alternative to context manager)."""
        if self._file_handle is None:
            self._file_handle = open(self.filepath, self.mode, encoding=self.encoding)

    def append(self, event: Event) -> None:
        """
        Append an event to the file.

        Args:
            event: Event to append

        Raises:
            HILTError: If write error occurs
        """
        if self._file_handle is None:
            raise HILTError("Session not opened. Use context manager or call open().")

        try:
            json_line = event.to_json()
            self._file_handle.write(json_line + "\n")
            self._file_handle.flush()  # Flush immediately to avoid data loss
        except Exception as e:
            raise HILTError(f"Failed to write event: {e}") from e

    def read(self) -> Iterator[Event]:
        """
        Read all events from the file.

        Yields:
            Event: Events one by one

        Raises:
            HILTError: If read or validation error occurs
        """
        if not self.filepath.exists():
            raise HILTError(f"File not found: {self.filepath}")

        with open(self.filepath, "r", encoding=self.encoding) as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue

                try:
                    event = Event.from_json(line)
                    yield event
                except Exception as e:
                    raise HILTError(f"Invalid event at line {line_num}: {e}") from e

    def close(self) -> None:
        """Close the file."""
        if self._file_handle is not None:
            self._file_handle.close()
            self._file_handle = None