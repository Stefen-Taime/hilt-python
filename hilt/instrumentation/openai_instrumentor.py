"""Auto-instrumentation for OpenAI SDK."""

from __future__ import annotations

import importlib
import time
from collections.abc import Callable
from types import ModuleType
from typing import Any, cast

from hilt.core.actor import Actor
from hilt.core.event import Content, Event, Metrics
from hilt.instrumentation.context import get_context
from hilt.integrations.openai import (
    _calculate_cost,
    _extract_status_code,
    _generate_conversation_uuid,
    _log_system_event,
    _unwrap_message_content,
    _usage_value,
)

chat_completions_module: ModuleType | None
try:  # pragma: no cover - runtime import guard
    chat_completions_module = importlib.import_module("openai.resources.chat.completions")
except ImportError:  # pragma: no cover - optional dependency
    chat_completions_module = None

OPENAI_AVAILABLE = chat_completions_module is not None


class OpenAIInstrumentor:
    """Instrumentor for OpenAI SDK."""

    def __init__(self) -> None:
        self._original_create: Callable[..., Any] | None = None
        self._is_instrumented = False

    def instrument(self) -> None:
        """Apply monkey-patching to OpenAI SDK."""
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI SDK not available")

        if self._is_instrumented:
            return

        if chat_completions_module is None:
            raise ImportError("OpenAI chat completions module unavailable")

        completions_module = cast(Any, chat_completions_module)

        # Conserve la méthode d'origine
        original = getattr(completions_module.Completions, "create")
        self._original_create = cast(Callable[..., Any], original)

        # Wrapper qui préserve 'self' du resource
        def instrumented_wrapper(completions_self: Any, *args: Any, **kwargs: Any) -> Any:
            return self._instrumented_create(completions_self, *args, **kwargs)

        setattr(completions_module.Completions, "create", instrumented_wrapper)

        self._is_instrumented = True
        print("✅ OpenAI SDK instrumented - all calls will be logged to HILT")

    def uninstrument(self) -> None:
        """Remove monkey-patching."""
        if not self._is_instrumented:
            return

        if self._original_create and chat_completions_module is not None:
            completions_module = cast(Any, chat_completions_module)
            setattr(completions_module.Completions, "create", self._original_create)

        self._is_instrumented = False

    def _instrumented_create(self, completions_self: Any, *args: Any, **kwargs: Any) -> Any:
        """Instrumented version of chat.completions.create()."""
        context = get_context()
        session = context.session

        # Si pas de session HILT, on passe à l'original
        if session is None:
            original = self._original_create
            if original is None:
                raise RuntimeError("OpenAIInstrumentor is not initialized")
            return original(completions_self, *args, **kwargs)

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
            actor=Actor(type="human", id="user"),
            action="prompt",
            content=Content(text=user_message),
        )
        session.append(prompt_event)

        start_time = time.time()

        try:
            # Appel OpenAI réel
            original = self._original_create
            if original is None:
                raise RuntimeError("OpenAIInstrumentor is not initialized")
            response = original(completions_self, *args, **kwargs)

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
                    actor=Actor(type="agent", id="openai"),
                    action="completion",
                    content=Content(text=assistant_message),
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


def instrument_openai() -> None:
    _instrumentor.instrument()


def uninstrument_openai() -> None:
    _instrumentor.uninstrument()


__all__ = ["OpenAIInstrumentor", "instrument_openai", "uninstrument_openai"]
