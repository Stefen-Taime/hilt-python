# Changelog

All notable changes to this project are documented here.

## [0.1.2] - 2025-10-08

### Added
- `hilt.instrument()` / `hilt.uninstrument()` for one-line auto-instrumentation
- OpenAI Chat Completions hook with automatic prompt/completion logging, latency, tokens, cost, and error tracking
- Append-only storage backends: local JSONL and Google Sheets with configurable columns
- Core telemetry schema (`Event`, `Actor`, `Content`, `Metrics`, `Session`) for advanced scenarios

### Removed
- Legacy helper patterns that required manual event construction per API call
- Interim CLI utilities (validate, stats, convert) and CSV/Parquet converters (will return in a future release)
