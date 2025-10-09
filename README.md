# HILT - Human-IA Log Trace

[![Build Status](https://img.shields.io/github/actions/workflow/status/hilt-format/hilt-python/test.yml?branch=main)](https://github.com/hilt-format/hilt-python/actions)
[![Coverage](https://img.shields.io/codecov/c/github/hilt-format/hilt-python)](https://codecov.io/gh/hilt-format/hilt-python)
[![PyPI](https://img.shields.io/pypi/v/hilt)](https://pypi.org/project/hilt/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

**HILT** (Human-IA Log Trace) is a privacy-first, vendor-neutral format for recording AI interactions. Capture prompts, completions, tool calls, metrics, and provenance across your AI stack.

## Features

- 🔒 **Privacy-aware** logging with hashing, encryption fields, and consent tracking.
- 📊 **Analytics-ready** exports via CSV and Parquet converters.
- 🛠 **Rich CLI tooling** for validation, statistics, and conversion pipelines.
- 🔌 **Integrations** with LangChain callbacks, OpenAI patterns, and Anthropic Claude helper.
- ⚙️ **Extensible schema** using Pydantic models and custom extensions.

## Installation

```bash
pip install hilt
```

Optional extras:

```bash
pip install "hilt[parquet,langchain]"
```

## Quickstart

Create and log your first event:

```python
from hilt import Session, Event, Actor, Content

event = Event(
    session_id="demo-session",
    actor=Actor(type="human", id="alice"),
    action="prompt",
    content=Content(text="Hello, AI!")
)

with Session("logs/demo.hilt.jsonl") as session:
    session.append(event)
```

Read events back:

```python
from hilt import Session

events = list(Session("logs/demo.hilt.jsonl", mode="r").read())
print(events[0].content.text)
```

Convert to CSV:

```python
from hilt.converters.csv import convert_to_csv

convert_to_csv("logs/demo.hilt.jsonl", "logs/demo.csv")
```

## CLI

```bash
hilt validate logs/demo.hilt.jsonl
hilt stats logs/demo.hilt.jsonl --json
hilt convert logs/demo.hilt.jsonl --to parquet --compression gzip
```

Refer to [docs/cli.md](docs/cli.md) for detailed options.

## Integrations

- LangChain callback handler: `HILTCallbackHandler`
- OpenAI helper pattern (see `examples/openai_integration.py`)
- Anthropic Claude helper: `log_claude_interaction`
- Google Gemini helper: `log_gemini_interaction`

More details in [docs/integrations.md](docs/integrations.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding standards, and release checklist. Join us in shaping the future of AI observability!

## Documentation

Full documentation lives in [docs/index.md](docs/index.md): installation, quickstart, API reference, CLI guide, integrations, privacy, advanced usage, contributing, and FAQ.

## License

Licensed under the [Apache License 2.0](LICENSE).
