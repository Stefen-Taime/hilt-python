# Advanced Usage

Push HILT beyond the basics: extend the schema, optimise performance, and operate at scale.

## Table of Contents

1. [Custom Extensions](#custom-extensions)
2. [Performance Optimisation](#performance-optimisation)
3. [Large-Scale Usage](#large-scale-usage)
4. [Multi-threading & Concurrency](#multi-threading--concurrency)

## Custom Extensions

- Use `Event.extensions` for domain-specific metadata (JSON-serialisable dicts).
- Add new actors/actions by reusing `Event.provenance` to document semantics.
- For schema enforcement, build Pydantic models atop `Event.model_copy(update=...)`.

```python
event = Event(...)
event.extensions = {"workflow_step": "rank_candidates"}
```

## Performance Optimisation

- Batch writes: append events in groups within a single session context.
- Disable `create_dirs` after initial startup to reduce filesystem checks.
- Convert to Parquet for analytics (columnar, compressed).
- Use the CLI progress bar (`hilt convert`) for large conversions.

## Large-Scale Usage

- Shard logs per day/week (`logs/2025-01-01/app.hilt.jsonl`).
- Push converted Parquet files to data warehouses (BigQuery, Snowflake, DuckDB).
- Automate validation in CI/CD (`hilt validate` + `hilt stats --json`).
- Monitor summary metrics for drift (tokens, latency, cost).
- Use the Google Sheets backend for rapid prototyping or manual QA reviews (`pip install "hilt[sheets]"`), customising columns to show only the metrics your team needs.

## Multi-threading & Concurrency

- The `Session` writer is append-only and safe for concurrent threads when each thread opens its own session context.
- For process-level concurrency, allocate separate files or use a queue/worker pattern.
- After crashes, reopen the session; HILT events are line-delimited, so partially written lines can be skipped during validation.
