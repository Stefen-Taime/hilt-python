# Integrations

HILT currently auto-instruments the official OpenAI Python SDK. Once you enable instrumentation, every call to `client.chat.completions.create()` is captured automatically—no wrappers or code changes required.

## OpenAI support

```python
from hilt import instrument
from openai import OpenAI

instrument(backend="local", filepath="logs/app.jsonl")

client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello!"}],
)
```

HILT logs:

- Prompts and completions as separate events
- Token usage, latency, and cost estimates
- HTTP-style status codes and error metadata
- Deterministic `conversation_id` values that link prompts to completions

Streaming responses (`stream=True`) are also supported—HILT records each chunk as `completion_chunk` events and emits a final `completion` event with the aggregated text and metrics.

## Storage backends

Choose the storage backend that fits your workflow:

- **Local JSONL (default)** – privacy-first, append-only logs that stay on disk.
- **Google Sheets** – optional real-time dashboard (`pip install "hilt[sheets]"`) with configurable columns for support or QA teams.

Switching backends does not require code changes beyond the original call to `instrument()`.

## Advanced controls

- Override sessions per thread with `get_context().use_session(...)` to route subsets of traffic to different files or dashboards.
- Call `uninstrument()` during shutdown to restore the original OpenAI SDK state.
- Append custom events manually via `Session.append(...)` for tool calls, guardrail feedback, or human review notes.

## Roadmap

Support for additional providers is planned, but today only OpenAI is available. If you are interested in helping expand coverage, check out [CONTRIBUTING](contributing.md) and open an issue or pull request.
