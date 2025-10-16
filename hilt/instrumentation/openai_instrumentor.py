"""Auto-instrumentation for OpenAI SDK."""

import time
from typing import Any

from hilt.core.event import Event, Metrics
from hilt.instrumentation.context import get_context
from hilt.integrations.openai import (
    _calculate_cost,
    _generate_conversation_uuid,
    _extract_status_code,
    _unwrap_message_content,
    _usage_value,
    _log_system_event,
)

try:
    from openai import OpenAI, OpenAIError, RateLimitError  # type: ignore
    from openai.resources.chat import completions as chat_completions_module  # type: ignore

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    chat_completions_module = None


class OpenAIInstrumentor:
    """Instrumentor for OpenAI SDK."""

    def __init__(self):
        self._original_create = None
        self._is_instrumented = False

    def instrument(self):
        """Apply monkey-patching to OpenAI SDK."""
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI SDK not available")

        if self._is_instrumented:
            return

        # Conserve la méthode d'origine
        self._original_create = chat_completions_module.Completions.create

        # Wrapper qui préserve 'self' du resource
        def instrumented_wrapper(completions_self, *args, **kwargs):
            return self._instrumented_create(completions_self, *args, **kwargs)

        chat_completions_module.Completions.create = instrumented_wrapper

        self._is_instrumented = True
        print("✅ OpenAI SDK instrumented - all calls will be logged to HILT")

    def uninstrument(self):
        """Remove monkey-patching."""
        if not self._is_instrumented:
            return

        if self._original_create:
            chat_completions_module.Completions.create = self._original_create

        self._is_instrumented = False

    def _instrumented_create(self, completions_self, *args, **kwargs):
        """Instrumented version of chat.completions.create()."""
        context = get_context()
        session = context.session

        # Si pas de session HILT, on passe à l'original
        if session is None:
            return self._original_create(completions_self, *args, **kwargs)

        model = kwargs.get("model", "gpt-4o-mini")
        messages = kwargs.get("messages", [])

        # Dernier message utilisateur (affiché dans l'event HILT mais
        # potentiellement exclu des logs via 'columns' côté Session)
        user_message = ""
        if messages:
            last_msg = messages[-1]
            if isinstance(last_msg, dict):
                user_message = last_msg.get("content", "") or ""

        # Génère un session_id stable pour ce run
        session_id = _generate_conversation_uuid(f"auto_{id(session)}")

        # Event prompt (humain)
        prompt_event = Event(
            session_id=session_id,
            actor={"type": "human", "id": "user"},
            action="prompt",
            content={"text": user_message},
        )
        session.append(prompt_event)

        start_time = time.time()

        try:
            # Appel OpenAI réel
            response = self._original_create(completions_self, *args, **kwargs)

            latency_ms = int((time.time() - start_time) * 1000)

            message = response.choices[0].message
            assistant_message = _unwrap_message_content(message)
            usage = getattr(response, "usage", None)

            prompt_tokens = _usage_value(usage, "prompt_tokens")
            completion_tokens = _usage_value(usage, "completion_tokens")
            total_tokens = _usage_value(usage, "total_tokens")

            cost_usd = _calculate_cost(model, prompt_tokens, completion_tokens)

            metrics = Metrics(
                tokens={
                    "prompt": prompt_tokens,
                    "completion": completion_tokens,
                    "total": total_tokens,
                },
                cost_usd=cost_usd,
            )

            extensions = {
                "reply_to": prompt_event.event_id,
                "model": model,
                "latency_ms": latency_ms,
                "status_code": 200,
            }

            # Event completion (agent)
            session.append(
                Event(
                    session_id=session_id,
                    actor={"type": "agent", "id": "openai"},
                    action="completion",
                    content={"text": assistant_message},
                    metrics=metrics,
                    extensions=extensions,
                )
            )

            return response

        except Exception as error:
            latency_ms = int((time.time() - start_time) * 1000)
            status_code = _extract_status_code(error)
            _log_system_event(
                session,
                session_id=session_id,
                reply_to=prompt_event.event_id,
                error_code="api_error",
                message=f"Error: {error}",
                latency_ms=latency_ms,
                status_code=status_code,
            )
            raise


_instrumentor = OpenAIInstrumentor()


def instrument_openai():
    _instrumentor.instrument()


def uninstrument_openai():
    _instrumentor.uninstrument()


__all__ = ["OpenAIInstrumentor", "instrument_openai", "uninstrument_openai"]
