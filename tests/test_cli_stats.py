from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from click.testing import CliRunner

from hilt.cli.main import cli
from hilt.core.event import Event


def _write_events(path: Path, events: list[Event]) -> None:
    path.write_text("\n".join(event.to_json() for event in events) + "\n", encoding="utf-8")


def _timestamp(days_offset: int = 0) -> str:
    base = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    return (base + timedelta(days=days_offset)).isoformat().replace("+00:00", "Z")


def test_stats_basic(tmp_path: Path) -> None:
    runner = CliRunner()
    events = [
        Event(
            session_id="sess-1",
            actor={"type": "human", "id": "alice"},
            action="prompt",
            metrics={"tokens": {"total": 50}, "cost_usd": 0.05, "latency_ms": 800},
            timestamp=_timestamp(0),
        ),
        Event(
            session_id="sess-1",
            actor={"type": "agent", "id": "gpt-4"},
            action="completion",
            metrics={"tokens": {"total": 60}, "cost_usd": 0.06, "latency_ms": 900},
            timestamp=_timestamp(0),
        ),
        Event(
            session_id="sess-2",
            actor={"type": "human", "id": "bob"},
            action="prompt",
            metrics={"tokens": {"total": 70}, "cost_usd": 0.07, "latency_ms": 1000},
            timestamp=_timestamp(1),
        ),
    ]
    file_path = tmp_path / "events.jsonl"
    _write_events(file_path, events)

    result = runner.invoke(cli, ["stats", str(file_path)])

    assert result.exit_code == 0
    assert "Total events" in result.output
    assert "3" in result.output
    assert "Unique sessions" in result.output
    assert "sess-2" not in result.output  # ensure IDs not leaked in overview
    assert "prompt" in result.output
    assert "Tokens" in result.output or "Total tokens" in result.output


def test_stats_empty_file(tmp_path: Path) -> None:
    runner = CliRunner()
    file_path = tmp_path / "empty.jsonl"
    file_path.write_text("", encoding="utf-8")

    result = runner.invoke(cli, ["stats", str(file_path)])

    assert result.exit_code == 0
    assert "No events found" in result.output


def test_stats_no_metrics(tmp_path: Path) -> None:
    runner = CliRunner()
    events = [
        Event(
            session_id="sess-1",
            actor={"type": "human", "id": "alice"},
            action="prompt",
            metrics=None,
            timestamp=_timestamp(0),
        )
    ]
    file_path = tmp_path / "events.jsonl"
    _write_events(file_path, events)

    result = runner.invoke(cli, ["stats", str(file_path)])

    assert result.exit_code == 0
    assert "No metrics data available." in result.output


def test_stats_json_output(tmp_path: Path) -> None:
    runner = CliRunner()
    events = [
        Event(
            session_id="sess-1",
            actor={"type": "human", "id": "alice"},
            action="prompt",
            metrics={"tokens": {"total": 100}, "latency_ms": 500},
            timestamp=_timestamp(0),
        ),
        Event(
            session_id="sess-2",
            actor={"type": "agent", "id": "gpt-4"},
            action="completion",
            metrics={"tokens": {"total": 200}, "latency_ms": 700},
            timestamp=_timestamp(1),
        ),
    ]
    file_path = tmp_path / "events.jsonl"
    _write_events(file_path, events)

    result = runner.invoke(cli, ["stats", str(file_path), "--json", "--period", "daily"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["total_events"] == 2
    assert data["unique_sessions"] == 2
    assert "metrics" in data
    assert data["metrics"]["total_tokens"] == 300
    assert "periods" in data
    assert len(data["periods"]) == 2


def test_stats_multiple_sessions(tmp_path: Path) -> None:
    runner = CliRunner()
    events = [
        Event(
            session_id=f"sess-{index}",
            actor={"type": "human", "id": f"user-{index}"},
            action="prompt",
            metrics={"tokens": {"total": 10}},
            timestamp=_timestamp(index),
        )
        for index in range(3)
    ]
    file_path = tmp_path / "events.jsonl"
    _write_events(file_path, events)

    result = runner.invoke(cli, ["stats", str(file_path)])

    assert result.exit_code == 0
    assert "Unique sessions" in result.output
    assert "3" in result.output
