from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Iterator

import pytest
from hilt.core.event import Event
from hilt.io.session import Session


def _make_event(index: int, session: str | None = None, actor_type: str = "human") -> Event:
    session_id = session or f"session-{index // 10}"
    actor = {"type": actor_type, "id": f"{actor_type}-{index}"}
    return Event(session_id=session_id, actor=actor, action="prompt")


def _event_stream(count: int) -> Iterator[Event]:
    for i in range(count):
        yield _make_event(i)


def test_complete_workflow_write_read(tmp_path: Path) -> None:
    jsonl_file = tmp_path / "complete.hilt.jsonl"

    with Session(jsonl_file) as session:
        for event in _event_stream(100):
            session.append(event)

    events = list(Session(jsonl_file, mode="r").read())
    assert len(events) == 100


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
    total_cost = sum(
        e.metrics.cost_usd for e in events if e.metrics and e.metrics.cost_usd is not None
    )
    assert pytest.approx(total_cost, rel=1e-3) == 0.024
