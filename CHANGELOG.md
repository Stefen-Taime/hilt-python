# Changelog

All notable changes to this project are documented here.

## [0.1.0] - 2025-10-08

### Added
- `hilt.instrument()` / `hilt.uninstrument()` for one-line auto-instrumentation
- OpenAI Chat Completions hook with automatic prompt/completion logging, latency, tokens, cost, and error tracking
- Append-only storage backends: local JSONL and Google Sheets with configurable columns
- Core telemetry schema (`Event`, `Actor`, `Content`, `Metrics`, `Session`) for advanced scenarios
- CLI commands (`hilt validate`, `hilt stats`, `hilt convert`) to keep logs healthy and analytics-ready

### Removed
- Legacy helper patterns that required manual event construction per API call
