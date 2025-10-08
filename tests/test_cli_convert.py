from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from hilt.cli.main import cli
from hilt.core.event import Event


def _write_jsonl(path: Path, events: list[Event]) -> None:
    path.write_text("\n".join(event.to_json() for event in events) + "\n", encoding="utf-8")


def test_convert_to_csv(tmp_path: Path) -> None:
    runner = CliRunner()
    events = [
        Event(session_id="s1", actor={"type": "human", "id": "alice"}, action="prompt"),
        Event(session_id="s1", actor={"type": "agent", "id": "bot"}, action="completion"),
    ]
    input_file = tmp_path / "events.jsonl"
    _write_jsonl(input_file, events)

    result = runner.invoke(cli, ["convert", str(input_file), "--to", "csv"])

    assert result.exit_code == 0
    output_file = input_file.with_suffix(".csv")
    assert output_file.exists()


def test_convert_to_parquet(tmp_path: Path) -> None:
    pytest.importorskip("pyarrow")
    runner = CliRunner()
    events = [
        Event(session_id="s1", actor={"type": "human", "id": "alice"}, action="prompt"),
    ]
    input_file = tmp_path / "events.jsonl"
    _write_jsonl(input_file, events)

    result = runner.invoke(
        cli,
        ["convert", str(input_file), "--to", "parquet", "--compression", "gzip"],
    )

    assert result.exit_code == 0
    output_file = input_file.with_suffix(".parquet")
    assert output_file.exists()


def test_convert_custom_output(tmp_path: Path) -> None:
    runner = CliRunner()
    events = [
        Event(session_id="s1", actor={"type": "human", "id": "alice"}, action="prompt"),
    ]
    input_file = tmp_path / "events.jsonl"
    _write_jsonl(input_file, events)
    output_file = tmp_path / "custom.csv"

    result = runner.invoke(
        cli,
        ["convert", str(input_file), "--to", "csv", "--output", str(output_file)],
    )

    assert result.exit_code == 0
    assert output_file.exists()


def test_convert_custom_columns(tmp_path: Path) -> None:
    runner = CliRunner()
    events = [
        Event(session_id="s1", actor={"type": "human", "id": "alice"}, action="prompt"),
    ]
    input_file = tmp_path / "events.jsonl"
    _write_jsonl(input_file, events)

    result = runner.invoke(
        cli,
        [
            "convert",
            str(input_file),
            "--to",
            "csv",
            "--columns",
            "event_id,timestamp,session_id",
        ],
    )

    assert result.exit_code == 0
    output_file = input_file.with_suffix(".csv")
    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert "event_id" in content
    assert "timestamp" in content


def test_convert_error_handling(tmp_path: Path) -> None:
    runner = CliRunner()
    input_file = tmp_path / "missing.jsonl"

    result = runner.invoke(cli, ["convert", str(input_file), "--to", "csv"])

    assert result.exit_code != 0
    assert "does not exist" in result.output
