"""Utilities for converting HILT JSONL event logs into CSV files."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

DEFAULT_COLUMNS: List[str] = [
    "event_id",
    "timestamp",
    "session_id",
    "actor.type",
    "actor.id",
    "action",
]


def convert_to_csv(
    input_file: str, output_file: str, columns: Optional[List[str]] = None
) -> None:
    """Convert a JSONL file of HILT events into a CSV file.

    Args:
        input_file: Path to the source JSONL file.
        output_file: Path where the CSV data should be written.
        columns: Optional list of columns to include in the CSV. When omitted,
            :data:`DEFAULT_COLUMNS` is used along with any additional keys discovered
            while processing the events (in encounter order).

    Raises:
        FileNotFoundError: If the input file does not exist.
        ValueError: If a line in the JSONL file contains invalid JSON.
    """
    resolved_input = Path(input_file)
    if not resolved_input.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    resolved_output = Path(output_file)
    fieldnames = list(columns) if columns is not None else list(DEFAULT_COLUMNS)
    rows: List[Dict[str, Any]] = []

    with resolved_input.open("r", encoding="utf-8") as source:
        for index, raw_line in enumerate(source, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON on line {index}: {error.msg}") from error
            flattened = _flatten_event(event)
            rows.append(flattened)
            if columns is None:
                _extend_fieldnames(fieldnames, flattened.keys())

    with resolved_output.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row_data in rows:
            writer.writerow({field: _normalize_value(row_data.get(field)) for field in fieldnames})


def _flatten_event(event: Any) -> Dict[str, Any]:
    """Flatten an event object into a dictionary with dot-separated keys."""
    if not isinstance(event, dict):
        raise ValueError("Each JSONL line must represent a JSON object.")
    flattened: Dict[str, Any] = {}
    _flatten_into(event, flattened)
    return flattened


def _flatten_into(value: Any, accumulator: Dict[str, Any], parent_key: str | None = None) -> None:
    """Recursively flatten a nested value into dot-notation keys."""
    if isinstance(value, dict):
        for key, child in value.items():
            new_key = f"{parent_key}.{key}" if parent_key else key
            _flatten_into(child, accumulator, new_key)
        return

    if isinstance(value, list):
        if parent_key is None:
            raise ValueError("Encountered a top-level list which cannot be flattened.")
        accumulator[parent_key] = _serialize_list(value)
        return

    if parent_key is None:
        raise ValueError("Encountered a top-level scalar which cannot be flattened.")

    accumulator[parent_key] = value


def _serialize_list(items: Iterable[Any]) -> str:
    """Serialize a list into either a semicolon-separated string or JSON."""
    items = list(items)
    if _is_simple_list(items):
        return ";".join("" if item is None else str(item) for item in items)
    return json.dumps(items, ensure_ascii=False)


def _is_simple_list(items: List[Any]) -> bool:
    """Return True if the list only contains simple scalar values."""
    simple_types = (str, int, float, bool, type(None))
    return all(isinstance(item, simple_types) for item in items)


def _extend_fieldnames(fieldnames: List[str], candidates: Iterable[str]) -> None:
    """Extend the CSV header with new fieldnames while preserving order."""
    for candidate in candidates:
        if candidate not in fieldnames:
            fieldnames.append(candidate)


def _normalize_value(value: Any) -> str:
    """Normalize values for CSV output, replacing None with an empty string."""
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)
