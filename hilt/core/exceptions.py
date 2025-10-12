"""Exceptions for HILT."""

from __future__ import annotations


class HILTError(Exception):
    """Base exception for HILT errors."""
    
    pass


class ValidationError(HILTError):
    """Raised when event validation fails."""
    
    pass


class SessionError(HILTError):
    """Raised when session operation fails."""
    
    pass


class ConversionError(HILTError):
    """Raised when format conversion fails."""
    
    pass


__all__ = [
    "HILTError",
    "ValidationError",
    "SessionError",
    "ConversionError",
]