"""Integration helpers for third-party frameworks."""

from .anthropic import log_claude_interaction
from .langchain import HILTCallbackHandler

__all__ = ["HILTCallbackHandler", "log_claude_interaction"]
