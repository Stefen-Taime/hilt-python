"""CLI command for validating HILT JSONL log files."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from hilt.core.event import Event

from .main import cli

CHECK_MARK = click.style("✓", fg="green")
CROSS_MARK = click.style("✗", fg="red")
VALID_LABEL = click.style("Valid", fg="green")
INVALID_LABEL = click.style("Invalid", fg="red")
WARNING_LABEL = click.style("Warning", fg="yellow")


@cli.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--verbose",
    is_flag=True,
    help="Show validation status for every event, not only failures.",
)
@click.option(
    "--max-errors",
    type=click.IntRange(1),
    default=None,
    help="Stop after reporting N errors.",
)
@click.pass_context
def validate(ctx: click.Context, file: Path, verbose: bool, max_errors: Optional[int]) -> None:
    """Validate a HILT JSONL file."""
    console = Console(file=click.get_text_stream("stdout"), highlight=False, soft_wrap=False)
    click.echo(f"Validating: {file}")

    total_events = 0
    valid_events = 0
    invalid_events = 0
    reported_errors = 0

    try:
        with file.open("r", encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line:
                    continue

                total_events += 1
                try:
                    Event.from_json(line)
                except Exception as error:  # noqa: BLE001 - surface validation issues
                    invalid_events += 1
                    reported_errors += 1
                    message = click.style(str(error), fg="red")
                    click.echo(f"{CROSS_MARK} Line {line_number}: {INVALID_LABEL} - {message}")
                    if max_errors is not None and reported_errors >= max_errors:
                        click.echo(f"{WARNING_LABEL} Reached max errors ({max_errors}). Stopping.")
                        total_events -= 1
                        break
                else:
                    valid_events += 1
                    if verbose:
                        click.echo(f"{CHECK_MARK} Line {line_number}: {VALID_LABEL}")
    except OSError as error:
        click.echo(click.style(f"Failed to read file: {error}", fg="red"), err=True)
        ctx.exit(1)

    _print_summary(console, total_events, valid_events, invalid_events)

    exit_code = 0 if invalid_events == 0 else 1
    ctx.exit(exit_code)


def _print_summary(console: Console, total: int, valid: int, invalid: int) -> None:
    console.print("Summary:", style="bold")
    table = Table(show_header=False, box=None, pad_edge=False)
    table.add_column(style="bold")
    table.add_column()
    table.add_row("Total events", str(total))
    table.add_row("Valid", f"[green]{valid} ({_as_percentage(valid, total)})[/]")
    table.add_row("Invalid", f"[red]{invalid} ({_as_percentage(invalid, total)})[/]")
    console.print(table)


def _as_percentage(count: int, total: int) -> str:
    if total == 0:
        return "0%"
    percentage = (count / total) * 100
    if percentage.is_integer():
        return f"{int(percentage)}%"
    return f"{percentage:.1f}%"
