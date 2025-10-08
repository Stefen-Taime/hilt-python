"""CLI command for computing statistics about HILT JSONL logs."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List, Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from hilt.core.event import Event
from hilt.core.exceptions import HILTError
from hilt.io.session import Session

from .main import cli


@dataclass
class PeriodStats:
    """Aggregated statistics for a specific time period."""

    events: int = 0
    tokens: int = 0
    cost: float = 0.0
    latencies: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "events": self.events,
            "tokens": self.tokens or None,
            "cost_usd": self.cost or None,
            "avg_latency_ms": mean(self.latencies) if self.latencies else None,
        }


@dataclass
class StatsResult:
    """Overall statistics."""

    total_events: int = 0
    session_ids: set[str] = field(default_factory=set)
    first_timestamp: Optional[datetime] = None
    last_timestamp: Optional[datetime] = None
    actions: Counter[str] = field(default_factory=Counter)
    actors: Counter[str] = field(default_factory=Counter)
    total_tokens: int = 0
    total_cost: float = 0.0
    latencies: List[int] = field(default_factory=list)
    period_stats: Dict[str, PeriodStats] = field(default_factory=dict)


@cli.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--json", "as_json", is_flag=True, help="Output statistics as JSON.")
@click.option(
    "--period",
    type=click.Choice(["daily", "weekly", "monthly"]),
    help="Aggregate time-series statistics.",
)
@click.pass_context
def stats(ctx: click.Context, file: Path, as_json: bool, period: Optional[str]) -> None:
    """Display statistics for a HILT JSONL log file."""
    console = Console()
    try:
        stats_result = _compute_stats(file, period)
    except HILTError as error:
        console.print(f"[red]Failed to read events: {error}[/]")
        ctx.exit(1)
    except Exception as error:  # noqa: BLE001
        console.print(f"[red]Unexpected error: {error}[/]")
        ctx.exit(1)

    if stats_result.total_events == 0:
        if as_json:
            click.echo(json.dumps({"file": str(file), "total_events": 0}, indent=2))
        else:
            console.print(f"[yellow]No events found in {file}.[/]")
        ctx.exit(0)

    if as_json:
        payload = _stats_to_json(stats_result, file, period)
        click.echo(json.dumps(payload, indent=2, default=str))
    else:
        _render_stats(console, stats_result, file, period)

    ctx.exit(0)


def _compute_stats(file: Path, period: Optional[str]) -> StatsResult:
    result = StatsResult()
    period_map: Dict[str, PeriodStats] = defaultdict(PeriodStats)

    session = Session(file, mode="r", create_dirs=False)
    for event in session.read():
        _update_overall_stats(result, event)
        if period:
            key = _period_key(_parse_timestamp(event.timestamp), period)
            period_map[key].events += 1
            tokens = _extract_tokens(event)
            if tokens is not None:
                period_map[key].tokens += tokens
            cost = _extract_cost(event)
            if cost is not None:
                period_map[key].cost += cost
            latency = _extract_latency(event)
            if latency is not None:
                period_map[key].latencies.append(latency)

    result.period_stats = dict(sorted(period_map.items()))
    return result


def _update_overall_stats(result: StatsResult, event: Event) -> None:
    result.total_events += 1
    result.session_ids.add(event.session_id)
    event_time = _parse_timestamp(event.timestamp)
    if result.first_timestamp is None or event_time < result.first_timestamp:
        result.first_timestamp = event_time
    if result.last_timestamp is None or event_time > result.last_timestamp:
        result.last_timestamp = event_time

    result.actions[event.action] += 1
    actor_label = event.actor.type
    if getattr(event.actor, "id", None):
        actor_label = f"{actor_label} ({event.actor.id})"
    result.actors[actor_label] += 1

    tokens = _extract_tokens(event)
    if tokens is not None:
        result.total_tokens += tokens

    cost = _extract_cost(event)
    if cost is not None:
        result.total_cost += cost

    latency = _extract_latency(event)
    if latency is not None:
        result.latencies.append(latency)


def _extract_tokens(event: Event) -> Optional[int]:
    if not event.metrics or not event.metrics.tokens:
        return None
    tokens = event.metrics.tokens
    if isinstance(tokens, dict):
        if "total" in tokens and isinstance(tokens["total"], int):
            return tokens["total"]
        total = 0
        for value in tokens.values():
            if isinstance(value, int):
                total += value
        return total
    return None


def _extract_cost(event: Event) -> Optional[float]:
    if not event.metrics or event.metrics.cost_usd is None:
        return None
    return float(event.metrics.cost_usd)


def _extract_latency(event: Event) -> Optional[int]:
    if not event.metrics or event.metrics.latency_ms is None:
        return None
    latency = event.metrics.latency_ms
    return int(latency) if isinstance(latency, (int, float)) else None


def _parse_timestamp(timestamp: str) -> datetime:
    text = timestamp.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _period_key(timestamp: datetime, period: str) -> str:
    if period == "daily":
        return timestamp.strftime("%Y-%m-%d")
    if period == "weekly":
        iso_year, iso_week, _ = timestamp.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"
    if period == "monthly":
        return timestamp.strftime("%Y-%m")
    raise ValueError(f"Unsupported period '{period}'.")


def _stats_to_json(result: StatsResult, file: Path, period: Optional[str]) -> Dict[str, object]:
    total = result.total_events
    payload: Dict[str, object] = {
        "file": str(file),
        "total_events": total,
        "unique_sessions": len(result.session_ids),
        "timeframe": {
            "start": result.first_timestamp.isoformat() if result.first_timestamp else None,
            "end": result.last_timestamp.isoformat() if result.last_timestamp else None,
            "duration_days": _duration_days(result.first_timestamp, result.last_timestamp),
        },
        "actions": _with_percentages(result.actions, total),
        "actors": _with_percentages(result.actors, total),
    }

    if result.total_tokens or result.total_cost or result.latencies:
        latencies = sorted(result.latencies)
        payload["metrics"] = {
            "total_tokens": result.total_tokens or None,
            "total_cost_usd": round(result.total_cost, 6) if result.total_cost else None,
            "average_latency_ms": _rounded(mean(latencies)) if latencies else None,
            "p50_latency_ms": _percentile(latencies, 50) if len(latencies) >= 10 else None,
            "p95_latency_ms": _percentile(latencies, 95) if len(latencies) >= 10 else None,
            "p99_latency_ms": _percentile(latencies, 99) if len(latencies) >= 10 else None,
        }

    if period and result.period_stats:
        payload["periods"] = [
            {"period": key, **stats.to_dict()} for key, stats in result.period_stats.items()
        ]

    return payload


def _with_percentages(counter: Counter[str], total: int) -> Dict[str, Dict[str, object]]:
    data: Dict[str, Dict[str, object]] = {}
    for key, count in counter.most_common():
        percentage = (count / total) * 100 if total else 0.0
        data[key] = {"count": count, "percentage": round(percentage, 2)}
    return data


def _render_stats(console: Console, result: StatsResult, file: Path, period: Optional[str]) -> None:
    console.print(f"[bold blue]📊 HILT Statistics: {file}[/]")
    console.rule()

    overview = Table(show_header=False, box=None, pad_edge=False)
    overview.add_column(style="bold")
    overview.add_column()
    overview.add_row("Total events", f"{result.total_events:,}")
    overview.add_row("Unique sessions", f"{len(result.session_ids):,}")
    timeframe = _format_timeframe(result.first_timestamp, result.last_timestamp)
    overview.add_row("Timeframe", timeframe)
    console.print(Panel(overview, title="Overview", border_style="cyan"))

    actions_table = _counter_table(result.actions, result.total_events, "Actions")
    if actions_table:
        console.print(actions_table)

    actors_table = _counter_table(result.actors, result.total_events, "Actors")
    if actors_table:
        console.print(actors_table)

    metrics_panel = _metrics_panel(result)
    if metrics_panel:
        console.print(metrics_panel)
    else:
        console.print("[yellow]No metrics data available.[/]")

    if period and result.period_stats:
        period_table = Table(title=f"{period.title()} Breakdown", box=None)
        period_table.add_column("Period", style="bold")
        period_table.add_column("Events", justify="right")
        period_table.add_column("Tokens", justify="right")
        period_table.add_column("Cost (USD)", justify="right")
        period_table.add_column("Avg latency (ms)", justify="right")
        for key, stats in result.period_stats.items():
            avg_latency = (
                f"{_rounded(mean(stats.latencies))}" if stats.latencies else "—"
            )
            period_table.add_row(
                key,
                f"{stats.events:,}",
                f"{stats.tokens:,}" if stats.tokens else "—",
                f"${stats.cost:,.2f}" if stats.cost else "—",
                avg_latency,
            )
        console.print(period_table)


def _counter_table(counter: Counter[str], total: int, title: str) -> Optional[Panel]:
    if not counter:
        return None
    table = Table(show_header=False, box=None, pad_edge=False)
    table.add_column(style="bold")
    table.add_column(justify="right")
    for label, count in counter.most_common():
        percentage = (count / total) * 100 if total else 0.0
        table.add_row(label, f"{count:,} ({percentage:.1f}%)")
    return Panel(table, title=title, border_style="magenta")


def _metrics_panel(result: StatsResult) -> Optional[Panel]:
    has_tokens = result.total_tokens > 0
    has_cost = result.total_cost > 0
    latencies = sorted(result.latencies)
    if not (has_tokens or has_cost or latencies):
        return None

    table = Table(show_header=False, box=None, pad_edge=False)
    table.add_column(style="bold")
    table.add_column(justify="right")

    if has_tokens:
        table.add_row("Total tokens", f"{result.total_tokens:,}")
    if has_cost:
        table.add_row("Total cost", f"${result.total_cost:,.2f}")
    if latencies:
        table.add_row("Avg latency", f"{_rounded(mean(latencies))} ms")
        if len(latencies) >= 10:
            table.add_row("P50 latency", f"{_percentile(latencies, 50)} ms")
            table.add_row("P95 latency", f"{_percentile(latencies, 95)} ms")
            table.add_row("P99 latency", f"{_percentile(latencies, 99)} ms")

    return Panel(table, title="Metrics", border_style="green")


def _format_timeframe(start: Optional[datetime], end: Optional[datetime]) -> str:
    if not (start and end):
        return "—"
    days = _duration_days(start, end)
    return f"{start.date()} → {end.date()} ({days} days)"


def _duration_days(start: Optional[datetime], end: Optional[datetime]) -> Optional[int]:
    if not (start and end):
        return None
    return (end.date() - start.date()).days + 1


def _percentile(data: Iterable[int], percentile: float) -> int:
    sorted_data = sorted(data)
    if not sorted_data:
        return 0
    k = (len(sorted_data) - 1) * (percentile / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_data) - 1)
    if f == c:
        return int(sorted_data[int(k)])
    d0 = sorted_data[f] * (c - k)
    d1 = sorted_data[c] * (k - f)
    return int(round(d0 + d1))


def _rounded(value: float) -> float:
    return round(value, 2)
