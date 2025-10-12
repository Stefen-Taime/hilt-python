# hilt/cli/convert.py
"""CLI command to convert HILT JSONL logs into other formats."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List, Optional

import click
from rich.console import Console
from rich.progress import BarColumn, Progress, TaskID, TextColumn, TimeElapsedColumn

from hilt.converters.csv import convert_to_csv
from hilt.converters.parquet import convert_to_parquet

from .main import cli


@cli.command()
@click.argument("input_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--to",
    "format",
    type=click.Choice(["csv", "parquet"]),
    required=True,
    help="Target format.",
)
@click.option("--output", type=click.Path(dir_okay=False, path_type=Path), default=None)
@click.option(
    "--columns",
    type=str,
    default=None,
    help="Comma-separated column names (CSV only, for flat format).",
)
@click.option(
    "--csv-format",  # 👈 NOUVEAU
    type=click.Choice(["readable", "detailed", "flat"]),
    default="readable",
    help="CSV output format: readable (default, 5 columns), detailed (11 columns with metadata), or flat (all columns, legacy).",
)
@click.option(
    "--compression",
    type=click.Choice(["snappy", "gzip", "none"]),
    default="snappy",
    help="Parquet compression codec.",
)
@click.pass_context
def convert(
    ctx: click.Context,
    input_file: Path,
    format: str,
    output: Optional[Path],
    columns: Optional[str],
    csv_format: str,  # 👈 NOUVEAU
    compression: str,
) -> None:
    """Convert HILT file to CSV or Parquet format.
    
    Examples:
    
        # Readable CSV (default) - 5 clean columns
        hilt convert logs/session.hilt.jsonl --to csv
        
        # Detailed CSV - 11 columns with metadata
        hilt convert logs/session.hilt.jsonl --to csv --csv-format detailed
        
        # Flat CSV (legacy) - all columns flattened
        hilt convert logs/session.hilt.jsonl --to csv --csv-format flat
        
        # Parquet format
        hilt convert logs/session.hilt.jsonl --to parquet
    """
    console = Console()
    try:
        output_path = output or _default_output_path(input_file, format)
        total_events = _count_events(input_file)
        progress = _create_progress(console)
        task = progress.add_task("Processing...", total=total_events if total_events else None)
        with progress:
            _run_conversion(
                format=format,
                input_file=input_file,
                output_file=output_path,
                columns=_parse_columns(columns),
                csv_format=csv_format,  # 👈 NOUVEAU
                compression=compression,
                progress=progress,
                task=task,
            )
        _print_success(console, format, input_file, output_path, total_events, csv_format)  # 👈 MODIFIÉ
    except Exception as error:  # noqa: BLE001 - surface CLI errors
        console.print(f"[red]Conversion failed: {error}[/]")
        ctx.exit(1)

    ctx.exit(0)


def _run_conversion(
    format: str,
    input_file: Path,
    output_file: Path,
    columns: Optional[List[str]],
    csv_format: str,  # 👈 NOUVEAU
    compression: str,
    progress: Progress,
    task: TaskID,
) -> None:
    if format == "csv":
        # Déterminer les paramètres selon le format CSV choisi
        if csv_format == "flat":
            # Mode legacy : ancien comportement avec colonnes aplaties
            convert_to_csv(
                str(input_file),
                str(output_file),
                columns=columns,
                readable=False
            )
        elif csv_format == "detailed":
            # Mode détaillé : format lisible avec toutes les métadonnées
            convert_to_csv(
                str(input_file),
                str(output_file),
                readable=True,
                include_metadata=True
            )
        else:  # "readable" (default)
            # Mode lisible : format simple et propre
            convert_to_csv(
                str(input_file),
                str(output_file),
                readable=True,
                include_metadata=False
            )
    elif format == "parquet":
        convert_to_parquet(str(input_file), str(output_file), compression=compression)
    else:  # pragma: no cover - safeguarded by click.Choice
        raise ValueError(f"Unsupported format '{format}'.")

    # Update progress to completion if total is known.
    if progress.tasks[task].total is not None:
        progress.update(task, completed=progress.tasks[task].total)


def _default_output_path(input_file: Path, format: str) -> Path:
    suffix = ".csv" if format == "csv" else ".parquet"
    return input_file.with_suffix(suffix)


def _parse_columns(columns: Optional[str]) -> Optional[List[str]]:
    if columns is None:
        return None
    return [column.strip() for column in columns.split(",") if column.strip()]


def _count_events(path: Path) -> int:
    count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                count += 1
    return count


def _create_progress(console: Console) -> Progress:
    return Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed} / {task.total}" if None else ""),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    )


def _print_success(
    console: Console,
    format: str,
    input_file: Path,
    output_file: Path,
    events: int,
    csv_format: str = "readable",  # 👈 NOUVEAU
) -> None:
    size = output_file.stat().st_size if output_file.exists() else 0
    human_size = _format_size(size)
    icon = click.style("✓", fg="green")
    console.print(
        f"{icon} Successfully converted to {format.upper()} ({events:,} events)",
    )
    console.print(f"  Output: {output_file} ({human_size})")
    
    # Afficher le format CSV utilisé
    if format == "csv":
        format_desc = {
            "readable": "readable (5 columns)",
            "detailed": "detailed (11 columns)",
            "flat": "flat (all columns)"
        }
        console.print(f"  Format: {format_desc.get(csv_format, csv_format)}")


def _format_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    index = 0
    size = float(size_bytes)
    while size >= 1024 and index < len(units) - 1:
        size /= 1024
        index += 1
    return f"{size:.1f} {units[index]}" if index > 0 else f"{int(size)} {units[0]}"