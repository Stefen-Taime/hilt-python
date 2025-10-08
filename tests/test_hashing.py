from __future__ import annotations

import pytest

from hilt.utils.hashing import hash_content, verify_hash


def test_hash_content_prefix() -> None:
    result = hash_content("hello")
    assert result.startswith("sha256:")


def test_verify_hash_success() -> None:
    content = "sample text"
    digest = hash_content(content)
    assert verify_hash(content, digest) is True


def test_verify_hash_failure() -> None:
    digest = hash_content("expected")
    assert verify_hash("other", digest) is False


def test_verify_hash_invalid_prefix() -> None:
    with pytest.raises(ValueError):
        verify_hash("content", "md5:deadbeef")

