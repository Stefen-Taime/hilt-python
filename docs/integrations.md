# Integrations

HILT automatically instruments LLM provider SDKs so you can log interactions without changing your application code.

## Supported providers

| Provider | Status | Notes |
|----------|--------|-------|
| OpenAI | ✅ Available | Instruments `client.chat.completions.create` |
| Anthropic | 🚧 Coming soon | Will follow the same auto-instrumentation pattern |
| Google Gemini | 🚧 Coming soon | Pending SDK stabilization |

## Quick start

```python
from hilt import instrument

# Enable auto-instrumentation (all available providers by default)
instrument(backend="local", filepath="logs/app.jsonl")
```

By default, `instrument()` enables every available provider. Today this means OpenAI; Anthropic and Gemini are on the way.

### Explicit provider selection

```python
instrument(
    backend="local",
    filepath="logs/app.jsonl",
    providers=["openai"],  # Explicit list
)
```

## OpenAI

When OpenAI instrumentation is active, HILT automatically:

- ✅ Captures every API call
  - Wraps `client.chat.completions.create()` transparently
  - Records streaming and non-streaming responses
  - Requires zero changes to your OpenAI usage
- ✅ Tracks conversation threads
  - Generates deterministic `conversation_id` values
  - Links completions to prompts via `reply_to`
- ✅ Records comprehensive metrics
  - Token usage (prompt, completion, total)
  - Calculated USD cost (based on current pricing)
  - Latency in milliseconds
  - HTTP-style status codes (200, 429, 500, …)
- ✅ Handles errors gracefully
  - Emits `system` events on exceptions
  - Captures rate limiting (429) and auth failures (401)

### What gets logged

Each API call generates two events.

**Prompt event**

```json
{
  "event_id": "evt_abc123",
  "session_id": "conv_a3f7d892",
  "actor": {"type": "human", "id": "user"},
  "action": "prompt",
  "content": {"text": "What is Python?"}
}
```

**Completion event**

```json
{
  "event_id": "evt_def456",
  "session_id": "conv_a3f7d892",
  "actor": {"type": "agent", "id": "openai"},
  "action": "completion",
  "content": {"text": "Python is a programming language..."},
  "metrics": {
    "tokens": {"prompt": 5, "completion": 87, "total": 92},
    "cost_usd": 0.000015
  },
  "extensions": {
    "reply_to": "evt_abc123",
    "model": "gpt-4o-mini",
    "latency_ms": 842,
    "status_code": 200
  }
}
```

### Streaming support

```python
from openai import OpenAI

client = OpenAI()

stream = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Count to 5"}],
    stream=True,
)

for chunk in stream:
    print(chunk.choices[0].delta.content, end="")
# ✅ All chunks logged automatically
# ✅ Final completion event includes full text + metrics
```

HILT emits one `completion_chunk` event per delta and a final `completion` event with the aggregated text and metrics.

### Error handling

When calls fail, HILT logs `system` events automatically:

```python
try:
    client.chat.completions.create(...)
except openai.RateLimitError:
    # HILT already logged a system event containing:
    # - error_code: "rate_limit"
    # - status_code: 429
    # - latency_ms: time until error
    raise
```

## Backend configuration

### Local JSONL (default)

```python
instrument(backend="local", filepath="logs/app.jsonl")
```

Best for:

- Development and production environments
- Privacy-sensitive workloads
- Offline analysis

### Google Sheets (real time)

```python
instrument(
    backend="sheets",
    sheet_id="1nduXlCD47mU2TiCJDgr29_K9wFg_vi1DpvflFsTHM44",
    credentials_path="credentials.json",
    worksheet_name="LLM Logs",
    columns=[
        "timestamp",
        "conversation_id",
        "reply_to",
        "message",
        "cost_usd",
        "status_code",
    ],
)
```

Ideal for:

- Team dashboards
- Stakeholder visibility
- Real-time cost monitoring

Features:

- Automatically creates the worksheet if missing
- Enforces headers and column order
- Streams events without buffering

Available columns:

- `timestamp`, `conversation_id`, `event_id`, `reply_to`, `status_code`
- `session`, `speaker`, `action`, `message`
- `tokens_in`, `tokens_out`, `cost_usd`, `latency_ms`
- `model`, `relevance_score`

Credentials setup:

```python
# Option 1: File path
instrument(
    backend="sheets",
    sheet_id="...",
    credentials_path="credentials.json",
)

# Option 2: Dict (e.g., env var)
import json, os

credentials = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
instrument(
    backend="sheets",
    sheet_id="...",
    credentials_json=credentials,
)
```

## Advanced usage

### Context-specific sessions

```python
from hilt import instrument
from hilt.instrumentation import get_context
from hilt.io.session import Session

instrument(backend="sheets", sheet_id="prod-sheet-id")

with Session("logs/debug.jsonl") as debug_session:
    with get_context().use_session(debug_session):
        # API calls here write to debug.jsonl instead of Sheets
        pass
```

Use cases:

- Separate logs for synthetic tests
- Debug workflows
- Per-customer routing or compliance

### Disable instrumentation

```python
from hilt import uninstrument

uninstrument()      # Stop logging all providers
instrument(...)     # Re-enable later
```

### Check instrumentation status

```python
from hilt.instrumentation import get_context

context = get_context()
print(f"Instrumented: {context.is_instrumented}")
print(f"Session: {context.session}")
```

## Coming soon

### Anthropic (Claude)

```python
# Planned
instrument(providers=["openai", "anthropic"])
```

### Google Gemini

```python
# Planned
instrument(providers=["openai", "gemini"])
```

## Migration from the manual API

Previously, you had to log interactions manually:

```python
from hilt import Session
from hilt.integrations.openai import log_chat_completion

with Session("logs/chat.jsonl") as session:
    log_chat_completion(session, user_message="Hello", model="gpt-4o-mini")
```

Now just instrument once:

```python
from hilt import instrument
from openai import OpenAI

instrument(backend="local", filepath="logs/chat.jsonl")

client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello"}],
)
# ✅ Logged automatically
```

Benefits:

- ✅ Less code to maintain
- ✅ No risk of forgetting to log
- ✅ Works with existing OpenAI usage

## Troubleshooting

**Nothing is being logged**

Call `instrument()` before importing the provider SDK:

```python
# ✅ Correct
from hilt import instrument
instrument(...)

from openai import OpenAI

# ❌ Incorrect
from openai import OpenAI
from hilt import instrument
instrument(...)  # Too late
```

**Instrumentation not working**

```python
from hilt.instrumentation import get_context

context = get_context()
print(context.is_instrumented)
print(context.session)
```

**Missing providers**

Ensure the provider SDK is installed:

```bash
pip install openai          # OpenAI
pip install anthropic       # Anthropic (when available)
pip install google-generativeai  # Gemini (when available)
```

## Contributing

Want to add support for another provider? See `CONTRIBUTING.md`. High-priority areas:

- Anthropic Messages instrumentation
- Google Gemini instrumentation
- Additional LLM providers (Cohere, AI21, etc.)

## Need help?

- Browse the rest of the docs for advanced usage and privacy guidance.
- Report issues or feature requests on GitHub. 🚀
