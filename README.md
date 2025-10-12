# HILT – Zero-Friction LLM Observability

[![Build Status](https://img.shields.io/github/actions/workflow/status/hilt-format/hilt-python/test.yml?branch=main)](https://github.com/hilt-format/hilt-python/actions)
[![Coverage](https://img.shields.io/codecov/c/github/hilt-format/hilt-python)](https://codecov.io/gh/hilt-format/hilt-python)
[![PyPI](https://img.shields.io/pypi/v/hilt)](https://pypi.org/project/hilt/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

HILT automatically captures every LLM interaction your application makes. Drop in one line at startup and get structured events with prompts, completions, metrics, and error context—no refactors, no custom wrappers.

## What’s inside today

- **One-line auto-instrumentation** for the official OpenAI Python SDK (`client.chat.completions.create`)
- **Deterministic conversation threading** with prompt/completion links and reply metadata
- **Rich telemetry**: latency, token usage, cost estimates, HTTP-style status codes, and error surfaces
- **Storage backends** you control: append-only JSONL files or real-time Google Sheets dashboards
- **Thread-safe context management** so you can override sessions per request, per worker, or per tenant
- **Manual event logging** via `Session.append()` for tool calls, human feedback, or guardrail results

## Installation

```bash
pip install hilt
```

Need Google Sheets streaming? Install the Sheets extra:

```bash
pip install "hilt[sheets]"
```

## Quick start

```python
from hilt import instrument, uninstrument
from openai import OpenAI

# Enable automatic logging (writes to logs/chat.jsonl by default)
instrument(backend="local", filepath="logs/chat.jsonl")

client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Give me three onboarding tips"}],
)

print(response.choices[0].message.content)

# Stop logging when your app shuts down
uninstrument()
```

After the single `instrument()` call:

- Prompts and completions are recorded as separate events
- Latency, tokens, cost, and status codes are populated automatically
- Conversation IDs remain stable so you can trace every exchange end to end

## Storage options

### Local JSONL (default)

```python
instrument(backend="local", filepath="logs/app.jsonl")
```

- Privacy-first: data never leaves your environment
- Plays nicely with analytics tooling (Python, Pandas, Spark, etc.)

### Google Sheets (real time)

```python
instrument(
    backend="sheets",
    sheet_id="1abc...",
    credentials_path="credentials.json",
    worksheet_name="LLM Logs",
    columns=["timestamp", "message", "cost_usd", "status_code"],
)
```

- Great for support, QA, or cost monitoring teams
- Columns control both ordering and visibility
- Works with `credentials_path` or in-memory `credentials_json`

## Advanced usage

### Provider selection

```python
instrument(
    backend="local",
    filepath="logs/app.jsonl",
    providers=["openai"],  # Anthropic / Gemini planned
)
```

Passing an empty list opens the session without patching any providers—useful for manual logging scenarios.

### Session overrides

```python
from hilt.instrumentation import get_context
from hilt.io.session import Session

debug_session = Session("logs/debug.jsonl")
debug_session.open()

with get_context().use_session(debug_session):
    # Only calls inside this block write to debug.jsonl
    client.chat.completions.create(...)
```

### Manual events

```python
from hilt import Event, Actor, Content
from hilt.instrumentation import get_context

session = get_context().session

session.append(
    Event(
        session_id="conv_custom",
        actor=Actor(type="system", id="guardrail"),
        action="feedback",
        content=Content(text="Response flagged for manual review"),
        extensions={"score": 0.42},
    )
)
```

## Troubleshooting highlights

- **Nothing recorded?** Ensure `instrument()` runs before importing the OpenAI client.
- **Async apps?** Use the same call; the instrumentation is thread-safe and works with `AsyncOpenAI`.
- **Large logs?** Rotate files daily (`logs/app-YYYY-MM-DD.jsonl`) and prune with a cron job.
- **Sheets failing?** Double-check the service account has editor access and that `hilt[sheets]` is installed.

See `docs/` for deeper guides on privacy, advanced contexts, and FAQ.

## Development

Contributions are welcome! Start with [CONTRIBUTING.md](CONTRIBUTING.md).The test suite lives in `tests/`, and linting/type checking is configured via Ruff, Black, and MyPy.

## License

Released under the [Apache License 2.0](LICENSE).
