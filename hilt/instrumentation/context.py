"""Thread-safe context for HILT instrumentation."""

import threading
from contextlib import contextmanager
from typing import Generator

from hilt.io.session import Session


class InstrumentationContext:
    """
    Global context for HILT instrumentation.

    Manages the active session and configuration in a thread-safe manner.
    """

    def __init__(self) -> None:
        self._local = threading.local()
        self._lock = threading.Lock()
        self._global_session: Session | None = None
        self._is_instrumented = False

    @property
    def session(self) -> Session | None:
        """Get the current thread's session or global session."""
        return getattr(self._local, "session", self._global_session)

    @session.setter
    def session(self, value: Session | None) -> None:
        """Set the current thread's session."""
        self._local.session = value

    @property
    def is_instrumented(self) -> bool:
        """Check if instrumentation is active."""
        return self._is_instrumented

    def set_global_session(self, session: Session) -> None:
        """Set the global session (used by all threads)."""
        with self._lock:
            self._global_session = session
            self._is_instrumented = True

    def clear(self) -> None:
        """Clear the instrumentation context."""
        with self._lock:
            self._global_session = None
            self._is_instrumented = False
            if hasattr(self._local, "session"):
                delattr(self._local, "session")

    @contextmanager
    def use_session(self, session: Session) -> Generator[None, None, None]:
        """
        Temporarily use a different session in this context.

        Example:
            >>> with context.use_session(my_session):
            ...     # All LLM calls here use my_session
            ...     response = client.chat.completions.create(...)
        """
        old_session = getattr(self._local, "session", None)
        self._local.session = session
        try:
            yield
        finally:
            if old_session is None:
                if hasattr(self._local, "session"):
                    delattr(self._local, "session")
            else:
                self._local.session = old_session


# Global singleton context
_context = InstrumentationContext()


def get_context() -> InstrumentationContext:
    """Get the global instrumentation context."""
    return _context


__all__ = ["InstrumentationContext", "get_context"]
