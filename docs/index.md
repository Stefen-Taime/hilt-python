# HILT Documentation

## What Is HILT?

HILT (Human‑IA Log Trace) is a vendor‑neutral logging format for recording AI interactions. Use it to capture prompts, completions, tool invocations, metrics, and privacy signals across human/AI sessions.

## Key Features

- 🧾 **Structured events** powered by Pydantic models (type-safe)
- 🧰 **Session writer/reader** for JSONL storage
- 🗂 **Flexible storage options** including Google Sheets with custom columns (requires `sheets` extra)
- 📊 **Converters** to CSV/Parquet for analytics
- 🛠 **CLI tools** for validation, stats, and conversion
- 🔌 **Integrations** for LangChain, OpenAI, Anthropic Claude, and custom callbacks
- 🌐 **Example API** powered by FastAPI + Uvicorn (requires `api` extra)
- 🔒 **Privacy-aware** design with hashing, timestamps, and extension fields

## Quick Example

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

## Documentation Map

- [Installation](installation.md)
- [Quickstart Tutorial](quickstart.md)
- [API Reference](api.md)
- [CLI Guide](cli.md)
- [Integrations](integrations.md)
- [Privacy & Compliance](privacy.md)
- [Advanced Usage](advanced.md)
- [Contributing](contributing.md)
- [FAQ](faq.md)
