# CLI Guide

The `hilt` command-line interface bundles validation, statistics, and conversion tooling.

## Table of Contents

1. [Overview](#overview)
2. [`hilt validate`](#hilt-validate)
3. [`hilt stats`](#hilt-stats)
4. [`hilt convert`](#hilt-convert)
5. [Combining Commands](#combining-commands)

## Overview

Install the CLI via `pip install hilt` or `poetry install` and run:

```bash
hilt --help
```

## `hilt validate`

Validate JSONL logs and surface malformed events.

```bash
hilt validate logs/app.hilt.jsonl
```

Options:

- `--verbose` – Show per-line status (`Valid`/`Invalid`).
- `--max-errors N` – Stop after N invalid events (useful for large files).

Example output:

```
Validating: logs/app.hilt.jsonl
✗ Line 42: Invalid - Invalid action: invalid_action
Summary:
Total events  350
Valid         349 (99.7%)
Invalid       1 (0.3%)
```

Non-zero exit codes indicate validation failures.

## `hilt stats`

Compute summaries for a log file.

```bash
hilt stats logs/app.hilt.jsonl
```

Key metrics:

- Total events, unique sessions, timeframe
- Action distribution (`prompt`, `completion`, …)
- Actor breakdown (`human`, `agent`, `tool`)
- Tokens, cost, latency (with P50/P95/P99 when ≥10 events)

Options:

- `--json` – Machine-readable JSON output.
- `--period daily|weekly|monthly` – Time-series aggregation.

## `hilt convert`

Streaming conversion to CSV or Parquet.

```bash
hilt convert logs/app.hilt.jsonl --to csv
hilt convert logs/app.hilt.jsonl --to parquet --compression gzip
```

Options:

- `--output` – Custom destination path (defaults to `.csv` / `.parquet`).
- `--columns` – Comma-separated column list for CSV.
- `--compression` – `snappy`, `gzip`, or `none` (Parquet only).

A Rich progress bar shows progress and completion stats.

## Combining Commands

Run validation and stats before conversion in CI/CD pipelines:

```bash
hilt validate logs/app.hilt.jsonl --max-errors 10 && \
  hilt stats logs/app.hilt.jsonl --json > reports/stats.json && \
  hilt convert logs/app.hilt.jsonl --to csv --output reports/app.csv
```

Refer to [Quickstart](quickstart.md) for programmatic usage.
