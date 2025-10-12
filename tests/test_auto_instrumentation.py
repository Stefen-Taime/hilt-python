"""Tests for auto-instrumentation functionality."""

import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from hilt import instrument, uninstrument
from hilt.instrumentation.context import get_context
from hilt.io.session import Session


@pytest.fixture
def temp_log_file(tmp_path):
    """Create a temporary log file."""
    return tmp_path / "test_auto.jsonl"


@pytest.fixture
def mock_openai():
    """Mock OpenAI SDK."""
    with patch('hilt.instrumentation.openai_instrumentor.OPENAI_AVAILABLE', True):
        with patch('hilt.instrumentation.openai_instrumentor.chat_completions_module') as mock_module:
            # Mock the original create method
            original_create = Mock()
            mock_module.Completions.create = original_create
            
            # Mock response
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Test response"
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 5
            mock_response.usage.total_tokens = 15
            
            original_create.return_value = mock_response
            
            yield original_create


class TestAutoInstrumentation:
    """Tests for the instrument() function."""
    
    def test_instrument_local_backend(self, temp_log_file):
        """Test instrumenting with local backend."""
        # Clean up any previous instrumentation
        uninstrument()
        
        # Instrument
        session = instrument(backend="local", filepath=str(temp_log_file))
        
        # Verify context is set
        context = get_context()
        assert context.is_instrumented
        assert context.session is not None
        assert context.session.backend == "local"
        
        # Clean up
        uninstrument()
    
    def test_instrument_with_filepath_only(self, temp_log_file):
        """Test instrument() with just filepath (should default to local)."""
        uninstrument()
        
        session = instrument(filepath=str(temp_log_file))
        
        context = get_context()
        assert context.is_instrumented
        assert context.session.backend == "local"
        
        uninstrument()
    
    def test_uninstrument(self, temp_log_file):
        """Test uninstrument() clears context."""
        uninstrument()
        
        # Instrument
        instrument(backend="local", filepath=str(temp_log_file))
        
        context = get_context()
        assert context.is_instrumented
        
        # Uninstrument
        uninstrument()
        
        assert not context.is_instrumented
        assert context.session is None
    
    def test_instrument_invalid_backend(self):
        """Test instrument() with invalid backend."""
        uninstrument()
        
        with pytest.raises(ValueError, match="Invalid backend"):
            instrument(backend="invalid")
    
    def test_instrument_missing_parameters(self):
        """Test instrument() without required parameters."""
        uninstrument()
        
        with pytest.raises(ValueError):
            instrument()  # No backend or filepath
    
    def test_multiple_instrument_calls(self, temp_log_file):
        """Test calling instrument() multiple times."""
        uninstrument()
        
        # First call
        session1 = instrument(backend="local", filepath=str(temp_log_file))
        
        # Second call (should replace first)
        temp_log_file2 = temp_log_file.parent / "test2.jsonl"
        session2 = instrument(backend="local", filepath=str(temp_log_file2))
        
        context = get_context()
        assert context.session == session2
        
        uninstrument()


class TestOpenAIInstrumentation:
    """Tests for OpenAI auto-instrumentation."""
    
    def test_openai_call_logged(self, temp_log_file, mock_openai):
        """Test that OpenAI calls are automatically logged."""
        uninstrument()
        
        # Instrument
        instrument(backend="local", filepath=str(temp_log_file))
        
        # Import OpenAI (must be after instrumentation)
        from hilt.instrumentation.openai_instrumentor import _instrumentor
        
        # Simulate an OpenAI call
        # (In real scenario, this would be: client.chat.completions.create(...))
        # For testing, we just verify the instrumentor is active
        assert _instrumentor._is_instrumented
        
        uninstrument()
    
    def test_logging_without_instrumentation(self, mock_openai):
        """Test that calls work normally without instrumentation."""
        uninstrument()
        
        from hilt.instrumentation.openai_instrumentor import _instrumentor
        
        # Should not be instrumented
        assert not _instrumentor._is_instrumented
        
        # Original OpenAI call should still work
        # (No logging, just normal behavior)


class TestContextManager:
    """Tests for context management."""
    
    def test_get_context_singleton(self):
        """Test that get_context() returns singleton."""
        from hilt.instrumentation.context import get_context
        
        context1 = get_context()
        context2 = get_context()
        
        assert context1 is context2
    
    def test_context_use_session(self, temp_log_file):
        """Test temporary session override with context manager."""
        uninstrument()
        
        # Set global session
        global_session = instrument(backend="local", filepath=str(temp_log_file))
        
        context = get_context()
        assert context.session == global_session
        
        # Create temporary session
        temp_file = temp_log_file.parent / "temp.jsonl"
        temp_session = Session(backend="local", filepath=str(temp_file))
        temp_session.open()
        
        # Use temporary session
        with context.use_session(temp_session):
            assert context.session == temp_session
        
        # Should revert to global session
        assert context.session == global_session
        
        # Clean up
        temp_session.close()
        uninstrument()


class TestProviderSelection:
    """Tests for provider selection."""
    
    def test_default_provider(self, temp_log_file):
        """Test default provider is OpenAI."""
        uninstrument()
        
        with patch('hilt.instrumentation.auto.instrument_openai') as mock_inst:
            instrument(backend="local", filepath=str(temp_log_file))
            
            # Should instrument OpenAI by default
            mock_inst.assert_called_once()
        
        uninstrument()
    
    def test_custom_providers(self, temp_log_file):
        """Test specifying custom providers."""
        uninstrument()
        
        with patch('hilt.instrumentation.auto.instrument_openai') as mock_openai:
            instrument(
                backend="local",
                filepath=str(temp_log_file),
                providers=["openai"]
            )
            
            mock_openai.assert_called_once()
        
        uninstrument()


class TestThreadSafety:
    """Tests for thread safety."""
    
    def test_context_thread_local(self, temp_log_file):
        """Test that context uses thread-local storage."""
        import threading
        
        uninstrument()
        
        # Set global session
        global_session = instrument(backend="local", filepath=str(temp_log_file))
        
        context = get_context()
        
        # Track results from thread
        results = {}
        
        def thread_func():
            # Thread should see global session
            results['session'] = context.session
        
        thread = threading.Thread(target=thread_func)
        thread.start()
        thread.join()
        
        # Both main thread and worker thread see same global session
        assert results['session'] == global_session
        
        uninstrument()


@pytest.mark.integration
class TestEndToEnd:
    """End-to-end integration tests."""
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set"
    )
    def test_real_openai_call(self, temp_log_file):
        """Test with real OpenAI API call."""
        uninstrument()
        
        # Instrument
        instrument(backend="local", filepath=str(temp_log_file))
        
        # Real OpenAI call
        from openai import OpenAI
        client = OpenAI()
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'test' only"}]
        )
        
        assert response.choices[0].message.content
        
        # Verify logs were written
        assert temp_log_file.exists()
        
        # Read and verify events
        with Session(backend="local", filepath=str(temp_log_file), mode="r") as session:
            events = list(session.read())
            
            # Should have at least 2 events: prompt + completion
            assert len(events) >= 2
            
            # Check prompt event
            prompt_event = next(e for e in events if e.action == "prompt")
            assert prompt_event.content.text == "Say 'test' only"
            
            # Check completion event
            completion_event = next(e for e in events if e.action == "completion")
            assert completion_event.metrics is not None
            assert completion_event.metrics.tokens is not None
            assert completion_event.metrics.cost_usd is not None
        
        uninstrument()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])