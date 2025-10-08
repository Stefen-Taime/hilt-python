from __future__ import annotations

from pathlib import Path
from click.testing import CliRunner

from hilt.cli.main import cli
from hilt.core.event import Event


def _write_events(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_validate_all_valid(tmp_path: Path) -> None:
    runner = CliRunner()
    events = [
        Event(session_id="s1", actor={"type": "human", "id": "alice"}, action="prompt").to_json(),
        Event(session_id="s1", actor={"type": "agent", "id": "bot"}, action="completion").to_json(),
    ]
    file_path = tmp_path / "events.jsonl"
    _write_events(file_path, events)

    result = runner.invoke(cli, ["validate", str(file_path)])

    assert result.exit_code == 0
    assert "Summary" in result.output
    assert "Invalid" in result.output
    assert "0%" in result.output


def test_validate_mixed_valid_invalid(tmp_path: Path) -> None:
    runner = CliRunner()
    lines = [
        Event(session_id="s1", actor={"type": "human", "id": "alice"}, action="prompt").to_json(),
        '{"session_id": "s1", "action": "prompt"}',
        Event(session_id="s1", actor={"type": "agent", "id": "bot"}, action="completion").to_json(),
    ]
    file_path = tmp_path / "events.jsonl"
    _write_events(file_path, lines)

    result = runner.invoke(cli, ["validate", str(file_path)])

    assert result.exit_code == 1
    assert "Line 2" in result.output
    assert "Invalid" in result.output
    assert "Reached max errors" not in result.output


def test_validate_file_not_found() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "missing.jsonl"])

    assert result.exit_code != 0
    assert "does not exist" in result.output


def test_validate_verbose(tmp_path: Path) -> None:
    runner = CliRunner()
    lines = [
        Event(session_id="s1", actor={"type": "human", "id": "alice"}, action="prompt").to_json(),
    ]
    file_path = tmp_path / "events.jsonl"
    _write_events(file_path, lines)

    result = runner.invoke(cli, ["validate", str(file_path), "--verbose"])

    assert result.exit_code == 0
    assert "Line 1: Valid" in result.output


def test_validate_max_errors(tmp_path: Path) -> None:
    runner = CliRunner()
    lines = [
        '{"session_id": "s1", "action": "prompt"}',
        '{"session_id": "s2", "action": "prompt"}',
        Event(session_id="s3", actor={"type": "agent", "id": "bot"}, action="completion").to_json(),
    ]
    file_path = tmp_path / "events.jsonl"
    _write_events(file_path, lines)

    result = runner.invoke(cli, ["validate", str(file_path), "--max-errors", "1"])

    assert result.exit_code == 1
    assert result.output.count("Invalid -") == 1
    assert "Reached max errors (1)" in result.output
