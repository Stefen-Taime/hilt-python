"""
HILT - Human-In-the-Loop Trace format
A lightweight format for logging AI interactions.
"""

from hilt.__version__ import __version__
from hilt.core.event import Event, Content, Metrics, Privacy, Actor
from hilt.core.exceptions import HILTError
from hilt.io.session import Session

__all__ = [
    "__version__",
    "Event",
    "Actor",
    "Content",
    "Metrics",
    "Privacy",
    "Session",
    "HILTError",
]
