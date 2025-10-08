from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

import pytest

pytest.importorskip("langchain")

from hilt.integrations.langchain import HILTCallbackHandler
from hilt.io.session import Session


def _fake_llm_result(text: str, model: str = "gpt-3.5-turbo") -> SimpleNamespace:
    generation = SimpleNamespace(text=text)
    return SimpleNamespace(
        generations=[[generation]],
        llm_output={
            "token_usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            },
            "model_name": model,
        },
    )


def _read_events(path: Path):
    return list(Session(path, mode="r").read())


def test_basic_llm_logging(tmp_path: Path) -> None:
    jsonl_file = tmp_path / "langchain_basic.jsonl"
    with Session(jsonl_file) as session:
        handler = HILTCallbackHandler(session, session_id="sess-basic")
        handler.on_chain_start({"name": "test_chain"}, {}, run_id="chain")
        handler.on_llm_start({"name": "fake_llm"}, ["Hello"], run_id="llm", parent_run_id="chain")
        handler.on_llm_end(_fake_llm_result("Hi"), run_id="llm", parent_run_id="chain")
        handler.on_chain_end({"output": "done"}, run_id="chain")

    events = _read_events(jsonl_file)
    actions = [event.action for event in events]
    assert actions == ["system", "prompt", "system", "completion", "system"]
    completion_event = events[3]
    assert completion_event.content.text == "Hi"
    assert completion_event.metrics.tokens["total"] == 30
    assert completion_event.metrics.cost_usd is not None


def test_tool_logging(tmp_path: Path) -> None:
    jsonl_file = tmp_path / "langchain_tool.jsonl"
    with Session(jsonl_file) as session:
        handler = HILTCallbackHandler(session, session_id="sess-tools")
        handler.on_chain_start({"name": "tool_chain"}, {}, run_id="chain")
        handler.on_tool_start({"name": "search"}, "query", run_id="tool", parent_run_id="chain")
        handler.on_tool_end("result", run_id="tool", parent_run_id="chain")
        handler.on_chain_end({"output": "done"}, run_id="chain")

    events = _read_events(jsonl_file)
    actions = [event.action for event in events]
    assert "tool_call" in actions
    assert "tool_result" in actions
    tool_call = next(event for event in events if event.action == "tool_call")
    assert tool_call.content.text == "query"
    tool_result = next(event for event in events if event.action == "tool_result")
    assert tool_result.content.text == "result"


def test_metrics_extraction_optional(tmp_path: Path) -> None:
    jsonl_file = tmp_path / "langchain_metrics.jsonl"
    with Session(jsonl_file) as session:
        handler = HILTCallbackHandler(session, session_id="sess-metrics", include_metrics=False)
        handler.on_chain_start({"name": "metrics_chain"}, {}, run_id="chain")
        handler.on_llm_start({"name": "fake"}, ["Prompt"], run_id="llm", parent_run_id="chain")
        handler.on_llm_end(_fake_llm_result("Completion"), run_id="llm", parent_run_id="chain")
        handler.on_chain_end({"output": "done"}, run_id="chain")

    completion_event = next(
        event
        for event in _read_events(jsonl_file)
        if event.action == "completion"
    )
    assert completion_event.metrics is None
