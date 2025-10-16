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

# Core
from hilt.core.event import Event, Content, Metrics
from hilt.core.actor import Actor
from hilt.core.exceptions import HILTError

# Session (advanced use)
from hilt.io.session import Session

# Main API - Auto-instrumentation
from hilt.instrumentation.auto import instrument, uninstrument

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
