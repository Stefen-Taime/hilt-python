# Integrations

HILT plays nicely with popular AI frameworks and SDKs. This page covers LangChain, OpenAI, Anthropic Claude, and patterns for custom integrations.

## Table of Contents

1. [LangChain](#langchain)
2. [OpenAI SDK](#openai-sdk)
3. [Anthropic Claude](#anthropic-claude)
4. [Custom Integrations](#custom-integrations)

## LangChain

Use the `HILTCallbackHandler` to automatically log LangChain chains, LLMs, and tools.

```python
from langchain.llms import OpenAI
from hilt.io.session import Session
from hilt.integrations.langchain import HILTCallbackHandler

with Session("logs/langchain.hilt.jsonl") as session:
    callback = HILTCallbackHandler(session, session_id="demo-chain")
    llm = OpenAI(callbacks=[callback])
    result = llm("Explain the HILT format in one sentence.")
```

The handler emits:

- `prompt` events for each input
- `completion` events with tokens/cost (when available)
- `tool_call` / `tool_result` events
- `system` events for chain boundaries

Install extras: `pip install "hilt[langchain]"`.

## OpenAI SDK

Use the `log_openai_call` helper (or roll your own) to record OpenAI chats.

See `examples/openai_integration.py` for a pattern that records prompt/completion pairs. The code boils down to:

```python
from openai import OpenAI
from hilt import Session, Event, Actor, Content, Metrics

client = OpenAI()
response = client.chat.completions.create(...)

with Session("logs/openai.hilt.jsonl") as session:
    session.append(Event(...))  # prompt
    session.append(Event(...))  # completion with Metrics(tokens=..., cost_usd=...)
```

## Anthropic Claude

```python
from anthropic import Anthropic
from hilt.io.session import Session
from hilt.integrations.anthropic import log_claude_interaction

client = Anthropic()
response = client.messages.create(...)

with Session("logs/claude.hilt.jsonl") as session:
    log_claude_interaction(session, user_message="Hello", response=response)
```

Tokens are extracted from `response.usage`; content blocks are flattened into event text.

## Google Gemini

```python
from google import generativeai as genai
from hilt.io.session import Session
from hilt.integrations.gemini import log_gemini_interaction

genai.configure(api_key="...")
model = genai.GenerativeModel("gemini-1.5-pro")
result = model.generate_content("Summarise the Solar System")

with Session("logs/gemini.hilt.jsonl") as session:
    log_gemini_interaction(session, user_message="Summarise the Solar System", response=result)
```

The helper pulls text from candidate parts and token counts from `usageMetadata` when available.

## Custom Integrations

When writing your own adapters:

1. Capture request/response payloads.
2. Construct `Event` instances that include metrics and metadata.
3. Use `Session` to append events.
4. Add provenance (`event.provenance`) for audit trails (e.g., model IDs, request IDs).

For inspiration, inspect `hilt/integrations/langchain.py` and `hilt/integrations/anthropic.py`.
