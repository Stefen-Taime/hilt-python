# HILT Documentation

**Zero-friction LLM observability for production applications.**

HILT automatically captures every LLM interaction with a single line of code. No wrappers, no refactoring—just automatic logging.

## What is HILT?

HILT (Human-In-the-Loop Tracing) provides automatic instrumentation for LLM APIs. After one setup call, every request is logged with full context:

- ✅ Prompts and completions – complete conversation history
- ✅ Token counts – prompt, completion, total
- ✅ Costs – USD estimates based on current pricing
- ✅ Performance – latency in milliseconds
- ✅ Status tracking – HTTP-style codes (200, 429, 500, …)
- ✅ Conversation threading – prompts and responses linked together

## Quick example

```python
from hilt import instrument
from openai import OpenAI

# Enable auto-logging (one line!)
instrument(backend="local", filepath="logs/app.jsonl")

# Your existing code works unchanged
client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello!"}],
)
# ✅ Automatically logged with full metrics
```

## Key features

**🚀 Zero code changes**  
Your OpenAI integration stays the same. Call `instrument()` during startup and keep shipping.

**💾 Flexible storage**

Local JSONL (privacy-first):

```python
instrument(backend="local", filepath="logs/app.jsonl")
```

Google Sheets (real-time dashboards):

```python
instrument(
    backend="sheets",
    sheet_id="1nduXlCD47mU2TiCJDgr29_K9wFg_vi1DpvflFsTHM44",
    credentials_path="credentials.json",
)
```

**📊 Rich metadata**

Every event includes unique conversation IDs, prompt/completion links, token usage, costs, latency, and error context.

**🔒 Privacy-aware**

- Local-first storage option
- Customisable column visibility for Sheets
- Open schema to attach compliance metadata
- Thread-safe context overrides

## Supported providers

| Provider | Status | Notes |
|----------|--------|-------|
| OpenAI | ✅ Available | Instruments `client.chat.completions.create` |

## Documentation

**Getting started**
- [Installation](installation.md) – install HILT and set up credentials
- [Quickstart](quickstart.md) – instrument an app in five minutes
- [Integrations](integrations.md) – provider-specific setup

**Guides**
- [Advanced usage](advanced.md) – context overrides, custom sessions, production tips
- [Privacy](privacy.md) – handling PII, compliance, and data subject rights
- [API reference](api.md) – complete API surface

**More**
- [Contributing](contributing.md) – how to get involved
- [FAQ](faq.md) – common questions and answers

## Architecture

```
Your Code → OpenAI SDK → HILT Instrumentation → OpenAI API
                              ↓
                         Event Logging
                              ↓
                    Local JSONL or Google Sheets
```

- `instrument()` monkey-patches the SDK
- HILT logs prompts before sending requests
- It logs completions after responses arrive
- Your code still receives the normal OpenAI response object

## Use cases

**🐛 Debugging** – Review all interactions to find regressions.

```python
from hilt import Session

with Session("logs/prod.jsonl", mode="r") as session:
    for event in session.read():
        status = event.extensions.get("status_code") if event.extensions else None
        if status and status >= 400:
            print(f"Error: {event.content.text}")
```

**💰 Cost tracking** – Monitor spend in real time with the Sheets backend.

**✅ Quality assurance** – Share dashboards with teams for quick review cycles.

**📈 Analytics** – Inspect token usage and latency trends.

```python
total_cost = 0.0
total_tokens = 0

with Session("logs/prod.jsonl", mode="r") as session:
    for event in session.read():
        if event.metrics and event.metrics.cost_usd:
            total_cost += event.metrics.cost_usd
            total_tokens += event.metrics.tokens.get("total", 0)

print(f"Total cost: ${total_cost:.4f}")
print(f"Total tokens: {total_tokens:,}")
```

**🔒 Compliance** – Maintain a complete audit trail for regulated environments.

## Why HILT?

**vs. manual logging**

- ✅ Zero code changes
- ✅ Impossible to forget logging
- ✅ Thread-safe execution

**vs. hosted observability tools**

- ✅ Free and open source
- ✅ Privacy-first (local by default)
- ✅ No extra API keys
- ✅ One-line setup

**vs. custom instrumentation**

- ✅ Battle-tested implementation
- ✅ Multiple storage backends
- ✅ Rich metadata baked in
- ✅ Actively maintained

## Community

- 📖 [GitHub](https://github.com/hilt-format/hilt-python)
- 🐛 [Report issues](https://github.com/hilt-format/hilt-python/issues)
- 💬 Discussions coming soon

## License

MIT License – see `LICENSE` for details.

Ready to start? Head over to [Installation](installation.md). 🚀
