import csv
import json
from pathlib import Path

import pytest

from hilt.converters.csv import DEFAULT_COLUMNS, convert_to_csv


def _write_jsonl(path: Path, records: list[dict]) -> None:
    lines = [json.dumps(record) for record in records]
    path.write_text("\n".join(lines), encoding="utf-8")


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    assert reader.fieldnames is not None
    return reader.fieldnames, rows


def test_convert_to_csv_basic(tmp_path: Path) -> None:
    input_path = tmp_path / "events.jsonl"
    output_path = tmp_path / "events.csv"
    _write_jsonl(
        input_path,
        [
            {
                "event_id": "abc",
                "timestamp": "2025-10-08T10:00:00Z",
                "session_id": "sess1",
                "actor": {"type": "human", "id": "alice"},
                "action": "prompt",
                "content": {"text": "Hello"},
                "metrics": {"tokens": {"total": 10}, "cost_usd": 0.001},
            }
        ],
    )

    convert_to_csv(str(input_path), str(output_path))
    header, rows = _read_csv(output_path)

    assert header == DEFAULT_COLUMNS + ["content.text", "metrics.tokens.total", "metrics.cost_usd"]
    assert rows == [
        {
            "event_id": "abc",
            "timestamp": "2025-10-08T10:00:00Z",
            "session_id": "sess1",
            "actor.type": "human",
            "actor.id": "alice",
            "action": "prompt",
            "content.text": "Hello",
            "metrics.tokens.total": "10",
            "metrics.cost_usd": "0.001",
        }
    ]


def test_convert_to_csv_custom_columns(tmp_path: Path) -> None:
    input_path = tmp_path / "events.jsonl"
    output_path = tmp_path / "events.csv"
    _write_jsonl(
        input_path,
        [
            {
                "event_id": "xyz",
                "timestamp": "2025-10-08T10:05:00Z",
                "session_id": "sess1",
                "content": {"text": "Hello"},
            }
        ],
    )

    columns = ["event_id", "content.text", "timestamp"]
    convert_to_csv(str(input_path), str(output_path), columns=columns)
    header, rows = _read_csv(output_path)

    assert header == columns
    assert rows == [
        {
            "event_id": "xyz",
            "content.text": "Hello",
            "timestamp": "2025-10-08T10:05:00Z",
        }
    ]


def test_convert_to_csv_missing_fields(tmp_path: Path) -> None:
    input_path = tmp_path / "events.jsonl"
    output_path = tmp_path / "events.csv"
    _write_jsonl(input_path, [{"event_id": "only-id"}])

    convert_to_csv(str(input_path), str(output_path))
    _, rows = _read_csv(output_path)

    assert rows == [
        {
            "event_id": "only-id",
            "timestamp": "",
            "session_id": "",
            "actor.type": "",
            "actor.id": "",
            "action": "",
        }
    ]


def test_convert_to_csv_nested_structures(tmp_path: Path) -> None:
    input_path = tmp_path / "events.jsonl"
    output_path = tmp_path / "events.csv"
    _write_jsonl(
        input_path,
        [
            {
                "event_id": "nested",
                "timestamp": "2025-10-08T10:10:00Z",
                "session_id": "sess2",
                "actor": {"type": "assistant", "id": "bot"},
                "action": "response",
                "metadata": {"level": {"sub": {"value": 123}}},
                "tags": ["alpha", "beta"],
                "chunks": [{"text": "hi"}, {"text": "bye"}],
            }
        ],
    )

    convert_to_csv(str(input_path), str(output_path))
    header, rows = _read_csv(output_path)

    assert "metadata.level.sub.value" in header
    assert "tags" in header
    assert "chunks" in header
    row = rows[0]
    assert row["metadata.level.sub.value"] == "123"
    assert row["tags"] == "alpha;beta"
    assert row["chunks"] == json.dumps([{"text": "hi"}, {"text": "bye"}], ensure_ascii=False)


def test_convert_to_csv_file_not_found(tmp_path: Path) -> None:
    output_path = tmp_path / "events.csv"
    with pytest.raises(FileNotFoundError):
        convert_to_csv(str(tmp_path / "missing.jsonl"), str(output_path))


def test_convert_to_csv_invalid_json(tmp_path: Path) -> None:
    input_path = tmp_path / "events.jsonl"
    output_path = tmp_path / "events.csv"
    input_path.write_text('{"event_id": "ok"}\n{"event_id": }\n', encoding="utf-8")

    with pytest.raises(ValueError) as excinfo:
        convert_to_csv(str(input_path), str(output_path))

    assert "Invalid JSON on line 2" in str(excinfo.value)
