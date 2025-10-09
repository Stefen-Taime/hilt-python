"""Integration helpers for third-party frameworks."""

from __future__ import annotations

from .anthropic import log_claude_interaction
from .gemini import log_gemini_interaction

try:  # Optional dependency
    from .langchain import HILTCallbackHandler
except ImportError:  # pragma: no cover
    HILTCallbackHandler = None  # type: ignore[misc,assignment]

__all__ = ["log_claude_interaction", "log_gemini_interaction", "HILTCallbackHandler"]
