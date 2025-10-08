"""HILT custom exceptions."""


class HILTError(Exception):
    """Base exception for HILT."""

    pass


class ValidationError(HILTError):
    """Event validation error."""

    pass


class FileError(HILTError):
    """File error (read/write)."""

    pass


class ConversionError(HILTError):
    """Format conversion error."""

    pass