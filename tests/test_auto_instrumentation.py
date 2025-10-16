"""Tests for auto-instrumentation functionality."""

import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch

from hilt import instrument, uninstrument
from hilt.instrumentation.context import get_context
from hilt.io.session import Session


@pytest.fixture
def temp_log_file(tmp_path: Path):
    """Create a temporary log file path."""
    return tmp_path / "test_auto.jsonl"


@pytest.fixture
def mock_openai():
    """
    Mock OpenAI SDK surface used by our instrumentor:
    - Expose chat_completions_module.Completions with a .create() method
    - Provide a fake client headers dict to carry OpenAI-Project
    - .create() returns a fake response with choices[0].message.content and usage
    """
    with patch('hilt.instrumentation.openai_instrumentor.OPENAI_AVAILABLE', True), \
         patch('hilt.instrumentation.openai_instrumentor.chat_completions_module') as mock_module:

        class _FakeMessage:
            # l'instrumentor utilise _unwrap_message_content(message)
            # qui sait extraire via .content
            content = "Test response"

        class _FakeChoice:
            message = _FakeMessage()

        class _FakeUsage:
            prompt_tokens = 10
            completion_tokens = 5
            total_tokens = 15

        class _FakeResponse:
            choices = [_FakeChoice()]
            usage = _FakeUsage()

        class _FakeClient:
            # headers au niveau client (fallback si pas d'extra_headers/env)
            headers = {"OpenAI-Project": "proj_from_client_123"}

        class Completions:
            def __init__(self):
                # le resource porte un _client que l’instrumentor peut inspecter
                self._client = _FakeClient()

            def create(self, *args, **kwargs):
                # méthode d’origine (sera sauvegardée par l’instrumentor)
                return _FakeResponse()

        mock_module.Completions = Completions
        yield mock_module  # permet d'accéder à la classe si besoin dans le test


class TestAutoInstrumentation:
    """Tests for the instrument() function."""

    def test_instrument_local_backend(self, temp_log_file: Path):
        uninstrument()
        session = instrument(backend="local", filepath=str(temp_log_file))
        context = get_context()
        assert context.is_instrumented
        assert context.session is not None
        assert context.session.backend == "local"
        uninstrument()

    def test_instrument_with_filepath_only(self, temp_log_file: Path):
        uninstrument()
        session = instrument(filepath=str(temp_log_file))
        context = get_context()
        assert context.is_instrumented
        assert context.session.backend == "local"
        uninstrument()

    def test_uninstrument(self, temp_log_file: Path):
        uninstrument()
        instrument(backend="local", filepath=str(temp_log_file))
        context = get_context()
        assert context.is_instrumented
        uninstrument()
        assert not context.is_instrumented
        assert context.session is None

    def test_instrument_invalid_backend(self):
        uninstrument()
        with pytest.raises(ValueError, match="Invalid backend"):
            instrument(backend="invalid")

    def test_instrument_missing_parameters(self):
        uninstrument()
        with pytest.raises(ValueError):
            instrument()  # No backend or filepath

    def test_multiple_instrument_calls(self, temp_log_file: Path):
        uninstrument()
        session1 = instrument(backend="local", filepath=str(temp_log_file))
        temp_log_file2 = temp_log_file.parent / "test2.jsonl"
        session2 = instrument(backend="local", filepath=str(temp_log_file2))
        context = get_context()
        assert context.session == session2
        uninstrument()


class TestOpenAIInstrumentation:
    """Tests for OpenAI auto-instrumentation."""

    def test_openai_call_logged_with_model_and_latency(self, temp_log_file: Path, mock_openai):
        """
        Instrumente, appelle la méthode patchée, puis vérifie:
        - 2 lignes (prompt + completion) écrites
        - la ligne completion contient model, latency_ms, status_code
        """
        uninstrument()

        # colonnes limitées pour assertions simples
        columns = ["timestamp", "action", "model", "latency_ms", "status_code"]
        instrument(backend="local", filepath=str(temp_log_file), columns=columns)

        # Utilise le module mocké que l'instrumentor a patché
        from hilt.instrumentation.openai_instrumentor import chat_completions_module
        completions = chat_completions_module.Completions()

        # Appel instrumenté : l’instrumentor doit intercepter et écrire 2 events
        _ = completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "ping"}],
        )

        # Lis le log
        lines = temp_log_file.read_text().splitlines()
        assert len(lines) == 2, f"Expected 2 events, got {len(lines)}"
        data = [json.loads(l) for l in lines]

        # On doit avoir les 2 actions
        actions = [d.get("action") for d in data]
        assert "prompt" in actions
        assert "completion" in actions

        # Récupère la ligne 'completion'
        completion = next(d for d in data if d.get("action") == "completion")

        # Asserts sur les colonnes choisies
        assert completion["model"] == "gpt-4o-mini"
        assert isinstance(completion["latency_ms"], int)
        assert completion["status_code"] == 200

        uninstrument()

    def test_logging_without_instrumentation(self, temp_log_file: Path, mock_openai):
        """
        Sans instrumentation active, l'appel passe mais aucun log n'est écrit.
        """
        uninstrument()
        from hilt.instrumentation.openai_instrumentor import chat_completions_module, _instrumentor
        assert not _instrumentor._is_instrumented

        # Appel direct de la méthode d'origine mockée
        completions = chat_completions_module.Completions()
        _ = completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": "hi"}])

        # Pas d'écriture attendue
        assert not temp_log_file.exists()


class TestContextManager:
    """Tests for context management."""

    def test_get_context_singleton(self):
        from hilt.instrumentation.context import get_context
        context1 = get_context()
        context2 = get_context()
        assert context1 is context2

    def test_context_use_session(self, temp_log_file: Path):
        uninstrument()
        global_session = instrument(backend="local", filepath=str(temp_log_file))
        context = get_context()
        assert context.session == global_session

        temp_file = temp_log_file.parent / "temp.jsonl"
        temp_session = Session(backend="local", filepath=str(temp_file))
        temp_session.open()

        with context.use_session(temp_session):
            assert context.session == temp_session

        assert context.session == global_session

        temp_session.close()
        uninstrument()


class TestProviderSelection:
    """Tests for provider selection."""

    def test_default_provider(self, temp_log_file: Path):
        uninstrument()
        with patch('hilt.instrumentation.auto.instrument_openai') as mock_inst:
            instrument(backend="local", filepath=str(temp_log_file))
            mock_inst.assert_called_once()
        uninstrument()

    def test_custom_providers(self, temp_log_file: Path):
        uninstrument()
        with patch('hilt.instrumentation.auto.instrument_openai') as mock_openai:
            instrument(backend="local", filepath=str(temp_log_file), providers=["openai"])
            mock_openai.assert_called_once()
        uninstrument()


class TestThreadSafety:
    """Tests for thread safety."""

    def test_context_thread_local(self, temp_log_file: Path):
        import threading

        uninstrument()
        global_session = instrument(backend="local", filepath=str(temp_log_file))
        context = get_context()

        results = {}

        def thread_func():
            results['session'] = context.session

        thread = threading.Thread(target=thread_func)
        thread.start()
        thread.join()

        assert results['session'] == global_session
        uninstrument()


@pytest.mark.integration
class TestEndToEnd:
    """End-to-end integration tests."""

    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
    def test_real_openai_call(self, temp_log_file: Path):
        uninstrument()
        instrument(backend="local", filepath=str(temp_log_file))

        from openai import OpenAI
        client = OpenAI()

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'test' only"}]
        )
        assert response.choices[0].message.content

        assert temp_log_file.exists()

        with Session(backend="local", filepath=str(temp_log_file), mode="r") as session:
            events = list(session.read())
            assert len(events) >= 2

            prompt_event = next(e for e in events if e.action == "prompt")
            assert prompt_event.content.text == "Say 'test' only"

            completion_event = next(e for e in events if e.action == "completion")
            assert completion_event.metrics is not None
            assert completion_event.metrics.tokens is not None
            assert completion_event.metrics.cost_usd is not None
            assert completion_event.metrics.cost_usd is not None

        uninstrument()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
