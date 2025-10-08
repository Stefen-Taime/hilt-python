"""Hashing helpers for HILT content fields."""

from __future__ import annotations

import hashlib

HASH_PREFIX = "sha256:"


def hash_content(content: str) -> str:
    """Return a namespaced SHA-256 hash for the given content string.

    Args:
        content: Arbitrary text content to hash.

    Returns:
        A string of the form ``sha256:<digest>`` where ``<digest>`` is the
        hexadecimal SHA-256 digest of ``content``.
    """
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return f"{HASH_PREFIX}{digest}"


def verify_hash(content: str, hash_str: str) -> bool:
    """Verify whether the provided content matches the given hash string.

    Args:
        content: Text content to validate.
        hash_str: A hash string produced by :func:`hash_content`.

    Returns:
        ``True`` if ``content`` matches ``hash_str``; ``False`` otherwise.

    Raises:
        ValueError: If ``hash_str`` does not use the expected prefix.
    """
    if not hash_str.startswith(HASH_PREFIX):
        raise ValueError("Hash must start with 'sha256:'.")
    expected = hash_content(content)
    return expected == hash_str
