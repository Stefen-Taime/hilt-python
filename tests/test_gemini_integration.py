from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from hilt.integrations.gemini import log_gemini_interaction
from hilt.io.session import Session


def _response(text: str, prompt_tokens: int = 8, completion_tokens: int = 16) -> SimpleNamespace:
    return SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[SimpleNamespace(text=text)],
                )
            )
        ],
        usageMetadata=SimpleNamespace(
            promptTokenCount=prompt_tokens,
            candidatesTokenCount=completion_tokens,
            totalTokenCount=prompt_tokens + completion_tokens,
        ),
    )


def test_log_gemini_interaction(tmp_path: Path) -> None:
    jsonl = tmp_path / "gemini.jsonl"
    with Session(jsonl) as session:
        log_gemini_interaction(
            session,
            user_message="Hi Gemini",
            response=_response("Hello!"),
            session_id="gemini-test",
            user_id="tester",
            assistant_id="gemini-pro",
        )

    events = list(Session(jsonl, mode="r").read())
    assert len(events) == 2
    assert events[0].action == "prompt"
    assert events[0].content.text == "Hi Gemini"
    completion = events[1]
    assert completion.action == "completion"
    assert completion.content.text == "Hello!"
    assert completion.metrics.tokens["total"] == 24
    assert completion.extensions["reply_to"] == events[0].event_id
