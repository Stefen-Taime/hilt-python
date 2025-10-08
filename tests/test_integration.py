from __future__ import annotations

import csv
import threading
import time
from pathlib import Path
from typing import Iterator

import pytest
from click.testing import CliRunner

from hilt.cli.main import cli
from hilt.converters.csv import convert_to_csv
from hilt.converters.parquet import convert_to_parquet
from hilt.core.event import Event
from hilt.io.session import Session


def _make_event(index: int, session: str | None = None, actor_type: str = "human") -> Event:
    session_id = session or f"session-{index // 10}"
    actor = {"type": actor_type, "id": f"{actor_type}-{index}"}
    return Event(session_id=session_id, actor=actor, action="prompt")


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def _event_stream(count: int) -> Iterator[Event]:
    for i in range(count):
        yield _make_event(i)


def test_complete_workflow_write_read_convert(tmp_path: Path) -> None:
    jsonl_file = tmp_path / "complete.hilt.jsonl"
    csv_file = tmp_path / "complete.hilt.csv"
    parquet_file = tmp_path / "complete.hilt.parquet"

    with Session(jsonl_file) as session:
        for event in _event_stream(100):
            session.append(event)

    events = list(Session(jsonl_file, mode="r").read())
    assert len(events) == 100

    convert_to_csv(str(jsonl_file), str(csv_file))
    assert csv_file.exists()
    assert len(_read_csv_rows(csv_file)) == 100

    pa = pytest.importorskip("pyarrow")
    pytest.importorskip("pyarrow.parquet")
    convert_to_parquet(str(jsonl_file), str(parquet_file))
    table = pa.parquet.read_table(parquet_file)
    assert table.num_rows == 100


def test_cli_workflow(tmp_path: Path) -> None:
    runner = CliRunner()
    jsonl_file = tmp_path / "cli.hilt.jsonl"
    csv_file = tmp_path / "cli.hilt.csv"

    events = [
        Event(session_id="sess-1", actor={"type": "human", "id": "alice"}, action="prompt"),
        Event(session_id="sess-1", actor={"type": "agent", "id": "bot"}, action="completion"),
    ]
    json_lines = [event.to_json() for event in events]
    json_lines.append('{"session_id": "sess-1"}')  # invalid event
    jsonl_file.write_text("\n".join(json_lines) + "\n", encoding="utf-8")

    result_validate = runner.invoke(cli, ["validate", str(jsonl_file)])
    assert result_validate.exit_code == 1
    assert "Invalid" in result_validate.output

    clean_jsonl = tmp_path / "cli_clean.hilt.jsonl"
    clean_jsonl.write_text("\n".join(json_lines[: len(events)]) + "\n", encoding="utf-8")

    result_stats = runner.invoke(cli, ["stats", str(clean_jsonl)])
    assert result_stats.exit_code == 0
    assert "Total events" in result_stats.output

    result_convert = runner.invoke(
        cli, ["convert", str(clean_jsonl), "--to", "csv", "--output", str(csv_file)]
    )
    assert result_convert.exit_code == 0
    assert csv_file.exists()
    rows = _read_csv_rows(csv_file)
    assert len(rows) == len(events)


def test_large_file_performance(tmp_path: Path) -> None:
    jsonl_file = tmp_path / "large.hilt.jsonl"
    total_events = 10_000

    start = time.perf_counter()
    with Session(jsonl_file) as session:
        for event in _event_stream(total_events):
            session.append(event)
    write_time = time.perf_counter()

    events = list(Session(jsonl_file, mode="r").read())
    read_time = time.perf_counter()

    assert len(events) == total_events
    total_elapsed = read_time - start
    write_elapsed = write_time - start
    read_elapsed = read_time - write_time
    assert write_elapsed < 5.0, f"Writing took too long: {write_elapsed:.2f}s"
    assert read_elapsed < 5.0, f"Reading took too long: {read_elapsed:.2f}s"
    assert total_elapsed < 5.0, f"Total duration exceeded limit: {total_elapsed:.2f}s"


def test_concurrent_writes(tmp_path: Path) -> None:
    jsonl_file = tmp_path / "concurrent.hilt.jsonl"
    total_threads = 5
    events_per_thread = 20

    def worker(offset: int) -> None:
        with Session(jsonl_file) as session:
            for index in range(events_per_thread):
                event = Event(
                    session_id=f"session-{offset}",
                    actor={"type": "human", "id": f"user-{offset}-{index}"},
                    action="prompt",
                )
                session.append(event)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(total_threads)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    events = list(Session(jsonl_file, mode="r").read())
    assert len(events) == total_threads * events_per_thread

    actor_ids = {event.actor.id for event in events}
    expected = {f"user-{t}-{i}" for t in range(total_threads) for i in range(events_per_thread)}
    assert actor_ids == expected


def test_error_recovery(tmp_path: Path) -> None:
    jsonl_file = tmp_path / "recovery.hilt.jsonl"

    session = Session(jsonl_file)
    session.open()
    try:
        for event in _event_stream(10):
            session.append(event)
        raise RuntimeError("Simulated crash")
    except RuntimeError:
        pass
    finally:
        session.close()

    initial_events = list(Session(jsonl_file, mode="r").read())
    assert len(initial_events) == 10

    with Session(jsonl_file) as resumed:
        for event in _event_stream(5):
            resumed.append(event)

    final_events = list(Session(jsonl_file, mode="r").read())
    assert len(final_events) == 15


def test_real_world_scenario(tmp_path: Path) -> None:
    jsonl_file = tmp_path / "chat.hilt.jsonl"
    csv_file = tmp_path / "chat.hilt.csv"

    turns = [
        {
            "session_id": "chat-1",
            "actor": {"type": "human", "id": "user"},
            "action": "prompt",
            "content": {"text": "Hello, who are you?"},
            "metrics": {"tokens": {"total": 12}, "cost_usd": 0.002, "latency_ms": 120},
        },
        {
            "session_id": "chat-1",
            "actor": {"type": "agent", "id": "assistant"},
            "action": "completion",
            "content": {"text": "I am an AI assistant."},
            "metrics": {"tokens": {"total": 30}, "cost_usd": 0.006, "latency_ms": 340},
        },
        {
            "session_id": "chat-1",
            "actor": {"type": "human", "id": "user"},
            "action": "prompt",
            "content": {"text": "Can you tell me a joke?"},
            "metrics": {"tokens": {"total": 15}, "cost_usd": 0.003, "latency_ms": 90},
        },
        {
            "session_id": "chat-1",
            "actor": {"type": "agent", "id": "assistant"},
            "action": "completion",
            "content": {"text": "Why did the AI cross the road? To optimize the route!"},
            "metrics": {"tokens": {"total": 40}, "cost_usd": 0.008, "latency_ms": 280},
        },
        {
            "session_id": "chat-1",
            "actor": {"type": "human", "id": "user"},
            "action": "prompt",
            "content": {"text": "Thanks!"},
            "metrics": {"tokens": {"total": 6}, "cost_usd": 0.001, "latency_ms": 70},
        },
        {
            "session_id": "chat-1",
            "actor": {"type": "agent", "id": "assistant"},
            "action": "completion",
            "content": {"text": "You're welcome!"},
            "metrics": {"tokens": {"total": 20}, "cost_usd": 0.004, "latency_ms": 200},
        },
    ]

    with Session(jsonl_file) as session:
        for payload in turns:
            session.append(Event(**payload))

    events = list(Session(jsonl_file, mode="r").read())
    assert len(events) == len(turns)
    assert sum(e.metrics.tokens["total"] for e in events if e.metrics and e.metrics.tokens) == 123

    convert_to_csv(str(jsonl_file), str(csv_file))
    rows = _read_csv_rows(csv_file)

    assert len(rows) == len(turns)
    aggregated_cost = sum(float(row.get("metrics.cost_usd") or 0) for row in rows)
    assert pytest.approx(aggregated_cost, rel=1e-3) == 0.024
