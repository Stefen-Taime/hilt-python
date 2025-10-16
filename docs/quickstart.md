# Quickstart

Get started with HILT.

## 1. Install HILT

```bash
pip install hilt-python
```

## 2. Set your OpenAI API key

```bash
export OPENAI_API_KEY="sk-..."  # macOS/Linux
```

On Windows PowerShell:

```powershell
$env:OPENAI_API_KEY="sk-..."
```

## 3. Enable auto-instrumentation (one line!)

```python
from hilt import instrument

# Enable automatic logging
instrument(backend="local", filepath="logs/chat.jsonl")
```

That’s it—HILT now captures every OpenAI Chat Completions call automatically.

## 4. Use OpenAI as normal

```python
from openai import OpenAI

client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "What are three best practices for API design?"}],
)

print(response.choices[0].message.content)
```

No changes to your existing code are required. HILT automatically records:

- ✅ Prompts and completions
- ✅ Token counts (input and output)
- ✅ Costs in USD
- ✅ Latency in milliseconds
- ✅ Status codes (200, 429, 500, …)

## 5. Inspect the logs

Your `logs/chat.jsonl` file now contains two events:

**Event 1 – Prompt**

```json
{
  "event_id": "evt_abc123",
  "timestamp": "2025-10-12T14:30:45Z",
  "session_id": "conv_a3f7d892",
  "actor": {"type": "human", "id": "user"},
  "action": "prompt",
  "content": {"text": "What are three best practices for API design?"}
}
```

**Event 2 – Completion**

```json
{
  "event_id": "evt_def456",
  "timestamp": "2025-10-12T14:30:46Z",
  "session_id": "conv_a3f7d892",
  "actor": {"type": "agent", "id": "openai"},
  "action": "completion",
  "content": {"text": "1. Use RESTful conventions..."},
  "metrics": {
    "tokens": {"prompt": 15, "completion": 87, "total": 102},
    "cost_usd": 0.000018
  },
  "extensions": {
    "reply_to": "evt_abc123",
    "model": "gpt-4o-mini",
    "latency_ms": 842,
    "status_code": 200
  }
}
```

### View logs programmatically

```python
from hilt import Session

with Session(backend="local", filepath="logs/chat.jsonl", mode="r") as session:
    for event in session.read():
        preview = event.content.text[:50] if event.content and event.content.text else ""
        print(f"{event.action}: {preview}...")
```

## 6. Google Sheets (real-time collaboration)

Want a live dashboard?

```bash
pip install "hilt-python[sheets]"
```

```python
from hilt import instrument

instrument(
    backend="sheets",
    sheet_id="1nduXlCD47mU2TiCJDgr29_K9wFg_vi1DpvflFsTHM44",
    credentials_path="credentials.json",
)
```

Events now appear in your Google Sheet instantly—ideal for:

- 📊 Team dashboards
- 💰 Cost monitoring
- 🐛 Debugging with non-technical stakeholders
- ✅ QA review

### Custom columns

Only want specific columns? Provide them explicitly:

```python
instrument(
    backend="sheets",
    sheet_id="...",
    columns=["timestamp", "message", "cost_usd", "status_code"],
)
```

Available columns: `timestamp`, `conversation_id`, `event_id`, `reply_to`, `status_code`, `session`, `speaker`, `action`, `message`, `tokens_in`, `tokens_out`, `cost_usd`, `latency_ms`, `model`, `relevance_score`.

## Complete example

```python
"""Complete HILT example."""

import os
from hilt import instrument
from openai import OpenAI

if not os.getenv("OPENAI_API_KEY"):
    print("Set OPENAI_API_KEY environment variable")
    raise SystemExit(1)

# Enable HILT (one line!)
instrument(backend="local", filepath="logs/app.jsonl")

client = OpenAI()

# First conversation
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "What is Python?"}],
)
print("Response 1:", response.choices[0].message.content)

# Second conversation (automatic conversation IDs)
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "What is JavaScript?"}],
)
print("Response 2:", response.choices[0].message.content)

print("\n✅ Both conversations logged to logs/app.jsonl")
```

## How it works

- `instrument()` monkey-patches the OpenAI SDK.
- Every `client.chat.completions.create()` call is intercepted once instrumentation is active.
- HILT logs the prompt, waits for the response, and logs the completion with metrics.
- Your code receives the same OpenAI response object.
- You can disable logging at any time using `uninstrument()`.

## Disable instrumentation

```python
from hilt import uninstrument

uninstrument()  # Stop logging
```

## Next steps

- Advanced usage – custom sessions and context overrides
- Privacy – best practices for sensitive data
- API reference – complete API documentation

## Troubleshooting

**Nothing is being logged**

Call `instrument()` before importing OpenAI:

```python
# ✅ Correct order
from hilt import instrument
instrument(...)

from openai import OpenAI  # Import after instrument()
```

**“Module not found” errors**

```bash
pip install hilt-python
pip install "hilt-python[sheets]"  # For Google Sheets support
```

Need more help? Check the docs or open an issue on GitHub. Parfait !
