"""Tests for OpenAI integration with enhanced metrics."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from hilt.integrations.openai import (
    OpenAIError,
    RateLimitError,
    log_chat_completion,
    log_chat_streaming,
    log_rag_interaction,
    _extract_status_code,
    _generate_conversation_uuid,
)
from hilt.io.session import Session


class _FakeCompletions:
    def __init__(self, response):
        self._response = response

    def create(self, **_: object):
        return self._response


class _FakeClient:
    def __init__(self, response):
        self.chat = SimpleNamespace(completions=_FakeCompletions(response))


def _response(text: str = "Hello!", prompt_tokens: int = 5, completion_tokens: int = 7):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
    )


def _create_mock_rate_limit_error():
    """Create a mock RateLimitError with required response and body."""
    mock_response = MagicMock()
    mock_response.status_code = 429
    error = RateLimitError(
        message="Rate limit exceeded",
        response=mock_response,
        body={"error": {"message": "Rate limit exceeded"}}
    )
    return error


def test_log_chat_completion_success(tmp_path: Path) -> None:
    """Test successful chat completion with metrics and status code."""
    jsonl = tmp_path / "openai.jsonl"
    client = _FakeClient(_response())

    with Session(jsonl) as session:
        log_chat_completion(
            session,
            user_message="Hi OpenAI",
            client=client,
            session_id="openai-test",
            assistant_id="gpt-4o-mini",
        )

    events = list(Session(jsonl, mode="r").read())
    assert len(events) == 2
    prompt_event, completion_event = events
    
    # Check basic structure
    assert prompt_event.action == "prompt"
    assert completion_event.action == "completion"
    assert completion_event.extensions["reply_to"] == prompt_event.event_id
    
    # Check metrics
    assert completion_event.metrics.tokens["total"] == 12
    assert completion_event.metrics.tokens["prompt"] == 5
    assert completion_event.metrics.tokens["completion"] == 7
    
    # Check status code
    assert completion_event.extensions["status_code"] == 200
    
    # Check model
    assert completion_event.extensions["model"] == "gpt-4o-mini"
    
    # Check latency exists
    assert "latency_ms" in completion_event.extensions
    
    # Check conversation UUID is generated
    assert prompt_event.session_id.startswith("conv_")
    assert completion_event.session_id == prompt_event.session_id


def test_log_chat_completion_rate_limit(tmp_path: Path) -> None:
    """Test rate limit error handling with status code."""
    class FailingCompletions:
        def create(self, **_: object):
            raise _create_mock_rate_limit_error()

    client = SimpleNamespace(chat=SimpleNamespace(completions=FailingCompletions()))
    jsonl = tmp_path / "openai_fail.jsonl"

    with Session(jsonl) as session:
        with pytest.raises(RateLimitError):
            log_chat_completion(
                session,
                user_message="Trigger error",
                client=client,
                session_id="openai-fail",
            )

    events = list(Session(jsonl, mode="r").read())
    assert len(events) == 2
    prompt_event, error_event = events
    
    # Check error event
    assert error_event.action == "system"
    assert error_event.extensions["reply_to"] == prompt_event.event_id
    assert error_event.extensions["error_code"] == "rate_limit"
    
    # Check status code is 429
    assert error_event.extensions["status_code"] == 429
    
    # Check latency is recorded
    assert "latency_ms" in error_event.extensions


def test_log_chat_completion_generic_error(tmp_path: Path) -> None:
    """Test generic API error handling with status code."""
    class FailingCompletions:
        def create(self, **_: object):
            error = OpenAIError("api failure")
            raise error

    client = SimpleNamespace(chat=SimpleNamespace(completions=FailingCompletions()))
    jsonl = tmp_path / "openai_api_error.jsonl"

    with Session(jsonl) as session:
        with pytest.raises(OpenAIError):
            log_chat_completion(
                session,
                user_message="Trigger api error",
                client=client,
                session_id="openai-api-error",
            )

    events = list(Session(jsonl, mode="r").read())
    assert len(events) == 2
    prompt_event, error_event = events
    
    # Check error event
    assert error_event.action == "system"
    assert error_event.extensions["reply_to"] == prompt_event.event_id
    assert error_event.extensions["error_code"] == "api_error"
    
    # Check status code defaults to 500
    assert error_event.extensions["status_code"] == 500


def test_log_chat_streaming_success(tmp_path: Path) -> None:
    """Test streaming chat completion with status codes."""
    chunk1 = SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content="Hello "))]
    )
    # chunk2 has both content and usage - this will generate both a chunk event and final completion
    chunk2 = SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content="world!"))],
        usage=SimpleNamespace(prompt_tokens=3, completion_tokens=4, total_tokens=7),
    )

    class StreamingCompletions:
        def create(self, **_: object):
            return iter([chunk1, chunk2])

    client = SimpleNamespace(chat=SimpleNamespace(completions=StreamingCompletions()))
    jsonl = tmp_path / "openai_stream.jsonl"

    with Session(jsonl) as session:
        log_chat_streaming(
            session,
            user_message="Hi OpenAI",
            client=client,
            session_id="openai-stream",
            assistant_id="gpt-4o-mini",
        )

    events = list(Session(jsonl, mode="r").read())
    # Expected: prompt, chunk1, chunk2 (because it has content), final completion
    assert [event.action for event in events] == ["prompt", "completion_chunk", "completion_chunk", "completion"]
    prompt_event = events[0]
    chunk_event_1 = events[1]
    chunk_event_2 = events[2]
    completion_event = events[3]
    
    # Check chunk events
    assert chunk_event_1.extensions["stream_index"] == 1
    assert chunk_event_1.extensions["reply_to"] == prompt_event.event_id
    assert chunk_event_1.extensions["status_code"] == 200
    
    assert chunk_event_2.extensions["stream_index"] == 2
    assert chunk_event_2.extensions["reply_to"] == prompt_event.event_id
    
    # Check completion event
    assert completion_event.content.text == "Hello world!"
    assert completion_event.metrics.tokens["total"] == 7
    assert completion_event.extensions["reply_to"] == prompt_event.event_id
    assert completion_event.extensions["status_code"] == 200
    assert completion_event.extensions["model"] == "gpt-4o-mini"


def test_log_rag_interaction(tmp_path: Path) -> None:
    """Test RAG interaction logging with full metrics and status codes."""
    jsonl = tmp_path / "rag.jsonl"
    documents = [
        {"id": "doc-1", "text": "Alpha doc", "score": 0.9, "metadata": {"source": "kb-1"}},
        {"id": "doc-2", "snippet": "Beta doc", "score": 0.8},
    ]

    with Session(jsonl) as session:
        log_rag_interaction(
            session,
            user_message="What is alpha?",
            answer="Alpha doc mentions ...",
            retrieved_documents=documents,
            session_id="rag-session",
            answer_metrics={
                "tokens": {"prompt": 10, "completion": 20, "total": 30},
                "cost_usd": 0.01,
                "latency_ms": 1500
            },
            model="gpt-4o-mini",
            retrieval_latency_ms=50,
        )

    events = list(Session(jsonl, mode="r").read())
    assert [event.action for event in events] == ["prompt", "retrieval", "retrieval", "completion"]
    
    prompt_event = events[0]
    retrieval_event_1 = events[1]
    retrieval_event_2 = events[2]
    completion_event = events[-1]
    
    # Check retrieval events
    assert retrieval_event_1.extensions["reply_to"] == prompt_event.event_id
    assert retrieval_event_1.extensions["doc_id"] == "doc-1"
    assert retrieval_event_1.extensions["status_code"] == 200
    assert retrieval_event_1.extensions["score"] == 0.9
    assert retrieval_event_1.extensions["latency_ms"] == 50
    
    assert retrieval_event_2.extensions["doc_id"] == "doc-2"
    assert retrieval_event_2.extensions["status_code"] == 200
    assert retrieval_event_2.extensions["score"] == 0.8
    
    # Check completion event
    assert completion_event.extensions["reply_to"] == prompt_event.event_id
    assert completion_event.extensions["retrieved_ids"] == ["doc-1", "doc-2"]
    assert completion_event.extensions["status_code"] == 200
    assert completion_event.extensions["model"] == "gpt-4o-mini"
    assert completion_event.extensions["latency_ms"] == 1500
    
    # Check metrics
    assert completion_event.metrics.tokens["total"] == 30
    assert completion_event.metrics.tokens["prompt"] == 10
    assert completion_event.metrics.tokens["completion"] == 20
    
    # Check conversation UUID
    assert prompt_event.session_id.startswith("conv_")


def test_extract_status_code_from_rate_limit_error() -> None:
    """Test extracting status code from RateLimitError."""
    error = _create_mock_rate_limit_error()
    status_code = _extract_status_code(error)
    assert status_code == 429


def test_extract_status_code_from_generic_error() -> None:
    """Test extracting status code from generic error."""
    error = OpenAIError("Unknown error")
    status_code = _extract_status_code(error)
    assert status_code == 500


def test_extract_status_code_from_error_with_attribute() -> None:
    """Test extracting status code from error with status_code attribute."""
    error = OpenAIError("Unauthorized")
    error.status_code = 401
    status_code = _extract_status_code(error)
    assert status_code == 401


def test_generate_conversation_uuid_deterministic() -> None:
    """Test that conversation UUID generation is deterministic."""
    uuid1 = _generate_conversation_uuid("rag_chat_1")
    uuid2 = _generate_conversation_uuid("rag_chat_1")
    
    # Same input should produce same UUID
    assert uuid1 == uuid2
    assert uuid1.startswith("conv_")
    
    # Different input should produce different UUID
    uuid3 = _generate_conversation_uuid("rag_chat_2")
    assert uuid1 != uuid3


def test_generate_conversation_uuid_format() -> None:
    """Test that conversation UUID has correct format."""
    uuid = _generate_conversation_uuid("test_session")
    
    # Should start with conv_
    assert uuid.startswith("conv_")
    
    # Should have 12 hex characters after conv_
    hex_part = uuid[5:]
    assert len(hex_part) == 12
    assert all(c in "0123456789abcdef" for c in hex_part)


def test_log_rag_interaction_with_cost_calculation(tmp_path: Path) -> None:
    """Test that RAG interaction calculates cost automatically."""
    jsonl = tmp_path / "rag_cost.jsonl"
    documents = [{"id": "doc-1", "text": "Test doc"}]

    with Session(jsonl) as session:
        log_rag_interaction(
            session,
            user_message="Test question",
            answer="Test answer",
            retrieved_documents=documents,
            session_id="rag-cost-test",
            answer_metrics={
                "tokens": {"prompt": 1000, "completion": 500, "total": 1500},
                "latency_ms": 2000
            },
            model="gpt-4o-mini",
        )

    events = list(Session(jsonl, mode="r").read())
    completion_event = events[-1]
    
    # Check that cost was calculated
    assert completion_event.metrics.cost_usd is not None
    assert completion_event.metrics.cost_usd > 0
    
    # Verify calculation: gpt-4o-mini pricing
    # Input: 1000 tokens * $0.150 / 1M = $0.00015
    # Output: 500 tokens * $0.600 / 1M = $0.0003
    # Total: $0.00045
    expected_cost = (1000 * 0.150 / 1_000_000) + (500 * 0.600 / 1_000_000)
    assert abs(completion_event.metrics.cost_usd - expected_cost) < 0.000001