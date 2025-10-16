"""
Auto-instrumentation for LLM providers.

This module provides automatic instrumentation for popular LLM SDKs,
enabling zero-code-change observability.

Example:
    >>> from hilt import instrument
    >>>
    >>> # Enable for OpenAI
    >>> instrument(backend="local", filepath="logs/chat.jsonl")
    >>>
    >>> # Your existing code works unchanged
    >>> from openai import OpenAI
    >>> client = OpenAI()
    >>> response = client.chat.completions.create(...)
    >>> # ✅ Automatically logged

Supported Providers:
    - OpenAI: ✅ Available
"""

from __future__ import annotations

from .auto import instrument, uninstrument
from .context import get_context, InstrumentationContext

# Provider-specific instrumentors (for advanced use)
from .openai_instrumentor import (
    OpenAIInstrumentor,
    instrument_openai,
    uninstrument_openai,
)

__all__ = [
    # Main API (recommended)
    "instrument",
    "uninstrument",
    # Context management (advanced)
    "get_context",
    "InstrumentationContext",
    # Provider-specific (advanced)
    "OpenAIInstrumentor",
    "instrument_openai",
    "uninstrument_openai",
]
