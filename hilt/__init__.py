"""
HILT - Human-In-the-Loop Tracing

Zero-friction LLM observability for production applications.

Quick Start:
    >>> from hilt import instrument
    >>>
    >>> instrument(backend="local", filepath="logs/chat.jsonl")
    >>>
    >>> from openai import OpenAI
    >>> client = OpenAI()
    >>> response = client.chat.completions.create(
    ...     model="gpt-4o-mini",
    ...     messages=[{"role": "user", "content": "Hello!"}]
    ... )
    >>> # ✅ Automatically logged!
"""

from hilt.__version__ import __version__
from hilt.core.actor import Actor

# Core
from hilt.core.event import Content, Event, Metrics
from hilt.core.exceptions import HILTError

# Main API - Auto-instrumentation
from hilt.instrumentation.auto import instrument, uninstrument

# Session (advanced use)
from hilt.io.session import Session

__all__ = [
    "__version__",
    "Event",
    "Content",
    "Metrics",
    "Actor",
    "HILTError",
    "Session",
    "instrument",
    "uninstrument",
]
