"""Conversion utilities for exporting HILT events to Parquet."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover - optional dependency
    tqdm = None

try:
    import pyarrow as _pa  # type: ignore
    import pyarrow.parquet as _pq  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    _pa = None  # type: ignore
    _pq = None  # type: ignore

if TYPE_CHECKING:
    import pyarrow as pa  # type: ignore
    import pyarrow.parquet as pq  # type: ignore
else:  # pragma: no branch
    pa = _pa  # type: ignore
    pq = _pq  # type: ignore

BATCH_SIZE = 1024
SUPPORTED_COMPRESSION = {"snappy", "gzip", "none"}
PARQUET_SCHEMA: Optional["pa.Schema"] = None


def convert_to_parquet(
    input_file: str, output_file: str, compression: str = "snappy"
) -> None:
    """Convert a JSONL file of HILT events to Parquet format.

    Args:
        input_file: Path to the source JSONL file.
        output_file: Path where the Parquet file should be written.
        compression: Compression codec to use (snappy, gzip, none).

    Raises:
        FileNotFoundError: If the input file does not exist.
        ValueError: If JSON decoding fails or an unsupported compression is requested.
        OSError: If writing to the destination fails.
    """
    resolved_input = Path(input_file)
    if not resolved_input.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    resolved_output = Path(output_file)
    codec = _normalize_compression(compression)
    schema = _get_schema()
    events = _read_events(resolved_input)

    progress = tqdm(desc="Converting JSONL to Parquet", unit="line") if tqdm else None

    writer: Optional["pq.ParquetWriter"] = None
    batch: List[Dict[str, Any]] = []
    try:
        for record in events:
            batch.append(record)
            if progress:
                progress.update(1)
            if len(batch) >= BATCH_SIZE:
                writer = _write_batch(batch, resolved_output, writer, codec, schema)
                batch.clear()
        if batch:
            writer = _write_batch(batch, resolved_output, writer, codec, schema)
        if writer is None:
            writer = _write_batch([], resolved_output, writer, codec, schema)
    finally:
        if progress:
            progress.close()
        if writer is not None:
            writer.close()


def _get_schema() -> "pa.Schema":
    global PARQUET_SCHEMA
    if pa is None or pq is None:
        raise ImportError(
            "PyArrow is required to use the Parquet converter. Install the 'hilt[parquet]' extra."
        )
    if PARQUET_SCHEMA is None:
        PARQUET_SCHEMA = pa.schema(
            [
                pa.field("event_id", pa.string(), nullable=False),
                pa.field("timestamp", pa.timestamp("ns", tz="UTC"), nullable=True),
                pa.field("session_id", pa.string(), nullable=True),
                pa.field("actor_type", pa.string(), nullable=True),
                pa.field("actor_id", pa.string(), nullable=True),
                pa.field("action", pa.string(), nullable=True),
                pa.field("content_text", pa.string(), nullable=True),
                pa.field("metrics_tokens_total", pa.int64(), nullable=True),
                pa.field("metrics_cost_usd", pa.float64(), nullable=True),
            ]
        )
    return PARQUET_SCHEMA


def _write_batch(
    batch: List[Dict[str, Any]],
    destination: Path,
    writer: Optional["pq.ParquetWriter"],
    codec: Optional[str],
    schema: "pa.Schema",
) -> "pq.ParquetWriter":
    table = _batch_to_table(batch, schema)
    if writer is None:
        writer = pq.ParquetWriter(str(destination), schema, compression=codec)
    writer.write_table(table)
    return writer


def _batch_to_table(batch: List[Dict[str, Any]], schema: "pa.Schema") -> "pa.Table":
    columns: Dict[str, List[Any]] = {field.name: [] for field in schema}
    for record in batch:
        for field in schema:
            columns[field.name].append(record.get(field.name))
    arrays = [
        pa.array(columns[field.name], type=field.type, from_pandas=True)
        for field in schema
    ]
    return pa.Table.from_arrays(arrays, schema=schema)


def _read_events(path: Path) -> Iterator[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON on line {line_number}: {error.msg}") from error
            yield _flatten_event(event)


def _flatten_event(event: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(event, dict):
        raise ValueError("Each JSONL line must represent a JSON object.")
    event_id = _as_str(event.get("event_id"))
    if event_id is None:
        raise ValueError("Event is missing required field 'event_id'.")
    actor = event.get("actor", {})
    metrics = event.get("metrics", {})
    tokens = metrics.get("tokens", {}) if isinstance(metrics, dict) else {}
    return {
        "event_id": event_id,
        "timestamp": _parse_timestamp(event.get("timestamp")),
        "session_id": _as_str(event.get("session_id")),
        "actor_type": _as_nested_str(actor, "type"),
        "actor_id": _as_nested_str(actor, "id"),
        "action": _as_str(event.get("action")),
        "content_text": _extract_content_text(event.get("content")),
        "metrics_tokens_total": _as_int(tokens.get("total")),
        "metrics_cost_usd": _as_float(metrics.get("cost_usd") if isinstance(metrics, dict) else None),
    }


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"Expected timestamp to be a string, received {type(value)!r}")
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as error:
        raise ValueError(f"Invalid timestamp format: {value}") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    else:
        parsed = parsed.astimezone(UTC)
    return parsed


def _extract_content_text(content: Any) -> Optional[str]:
    if isinstance(content, dict):
        return _as_nested_str(content, "text")
    if isinstance(content, str):
        return content
    return None


def _as_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value)


def _as_nested_str(container: Any, key: str) -> Optional[str]:
    if isinstance(container, dict):
        value = container.get(key)
        return _as_str(value) if value is not None else None
    return None


def _as_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str) and value.strip():
        try:
            return int(value)
        except ValueError:
            try:
                return int(float(value))
            except ValueError as error:
                raise ValueError(f"Invalid integer value: {value}") from error
    return None


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value)
        except ValueError as error:
            raise ValueError(f"Invalid float value: {value}") from error
    return None


def _normalize_compression(codec: str) -> Optional[str]:
    normalized = codec.lower()
    if normalized not in SUPPORTED_COMPRESSION:
        raise ValueError(
            f"Unsupported compression '{codec}'. Expected one of {SUPPORTED_COMPRESSION}."
        )
    return None if normalized == "none" else normalized
