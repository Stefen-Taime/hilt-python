from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

from hilt.integrations.anthropic import log_claude_interaction
from hilt.io.session import Session


def _response(text: str, prompt_tokens: int = 5, completion_tokens: int = 7) -> SimpleNamespace:
    return SimpleNamespace(
        content=[{"text": text}],
        usage=SimpleNamespace(
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
    )


def test_log_claude_interaction(tmp_path: Path) -> None:
    jsonl = tmp_path / "claude.jsonl"
    with Session(jsonl) as session:
        log_claude_interaction(
            session,
            user_message="Hello Claude",
            response=_response("Hi there!"),
            session_id="claude-test",
        )

    events = list(Session(jsonl, mode="r").read())
    assert len(events) == 2
    assert events[0].action == "prompt"
    assert events[0].content.text == "Hello Claude"
    assert events[1].action == "completion"
    assert events[1].content.text == "Hi there!"
    assert events[1].metrics.tokens["total"] == 12
    assert events[1].extensions["reply_to"] == events[0].event_id
