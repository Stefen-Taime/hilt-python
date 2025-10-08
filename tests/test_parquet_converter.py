import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pytest

pa = pytest.importorskip("pyarrow")
pq = pytest.importorskip("pyarrow.parquet")

from hilt.converters.parquet import convert_to_parquet


def _write_jsonl(path: Path, records: Iterable[dict]) -> None:
    lines = [json.dumps(record) for record in records]
    path.write_text("\n".join(lines), encoding="utf-8")


def _read_parquet(path: Path) -> pa.Table:
    return pq.read_table(path)


def test_convert_to_parquet_basic(tmp_path: Path) -> None:
    input_path = tmp_path / "events.jsonl"
    output_path = tmp_path / "events.parquet"
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

    convert_to_parquet(str(input_path), str(output_path))
    table = _read_parquet(output_path)

    assert table.num_rows == 1
    record = table.to_pydict()
    assert record["event_id"] == ["abc"]
    assert record["session_id"] == ["sess1"]
    assert record["actor_type"] == ["human"]
    assert record["actor_id"] == ["alice"]
    assert record["action"] == ["prompt"]
    assert record["content_text"] == ["Hello"]
    assert record["metrics_tokens_total"] == [10]
    assert record["metrics_cost_usd"] == [0.001]

    timestamp = table.column("timestamp")[0].as_py()
    assert isinstance(timestamp, datetime)
    assert timestamp.tzinfo is not None
    assert timestamp.tzinfo.utcoffset(timestamp) == timezone.utc.utcoffset(timestamp)


@pytest.mark.parametrize("compression", ["snappy", "gzip", "none"])
def test_convert_to_parquet_with_compression(tmp_path: Path, compression: str) -> None:
    input_path = tmp_path / f"events_{compression}.jsonl"
    output_path = tmp_path / f"events_{compression}.parquet"
    _write_jsonl(input_path, [{"event_id": compression, "timestamp": "2025-10-08T10:00:00Z"}])

    convert_to_parquet(str(input_path), str(output_path), compression=compression)
    table = _read_parquet(output_path)

    assert table.num_rows == 1
    pq_file = pq.ParquetFile(output_path)
    codec = pq_file.metadata.row_group(0).column(0).compression
    expected = {"snappy": "SNAPPY", "gzip": "GZIP", "none": "UNCOMPRESSED"}[compression]
    assert str(codec).upper() == expected


def test_convert_to_parquet_missing_optional_fields(tmp_path: Path) -> None:
    input_path = tmp_path / "events.jsonl"
    output_path = tmp_path / "events.parquet"
    _write_jsonl(input_path, [{"event_id": "missing-fields"}])

    convert_to_parquet(str(input_path), str(output_path))
    table = _read_parquet(output_path)
    record = table.to_pydict()

    assert record["event_id"] == ["missing-fields"]
    assert record["session_id"] == [None]
    assert record["actor_type"] == [None]
    assert record["actor_id"] == [None]
    assert record["action"] == [None]
    assert record["content_text"] == [None]
    assert record["metrics_tokens_total"] == [None]
    assert record["metrics_cost_usd"] == [None]


def test_convert_to_parquet_large_file(tmp_path: Path) -> None:
    input_path = tmp_path / "events.jsonl"
    output_path = tmp_path / "events.parquet"
    total_events = 2050  # ensures multiple batches
    records = [
        {
            "event_id": f"id-{index}",
            "timestamp": "2025-10-08T10:00:00Z",
            "session_id": f"sess-{index % 5}",
            "actor": {"type": "assistant", "id": "bot"},
            "action": "response",
            "metrics": {"tokens": {"total": index}},
        }
        for index in range(total_events)
    ]
    _write_jsonl(input_path, records)

    convert_to_parquet(str(input_path), str(output_path))
    table = _read_parquet(output_path)

    assert table.num_rows == total_events
    assert table.column("metrics_tokens_total").to_pylist()[-1] == total_events - 1


def test_convert_to_parquet_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        convert_to_parquet(str(tmp_path / "missing.jsonl"), str(tmp_path / "out.parquet"))
