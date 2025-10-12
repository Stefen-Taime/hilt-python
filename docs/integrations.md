# Integrations

HILT plays nicely with popular AI frameworks and SDKs. This page covers LangChain, OpenAI, Anthropic Claude, and patterns for custom integrations.

## Table of Contents

1. [LangChain](#langchain)
2. [OpenAI SDK](#openai-sdk)
3. [Anthropic Claude](#anthropic-claude)
4. [Google Gemini](#google-gemini)
5. [REST API Example](#rest-api-example)
6. [Custom Integrations](#custom-integrations)

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

Use the convenience helpers for chat completions, streaming output, and RAG logging. Each helper now:

- Converts simple session IDs into deterministic conversation UUIDs.
- Records latency, token usage, and cost (based on current OpenAI pricing).
- Stores HTTP-like status codes and `reply_to` links for traceability.
- Emits `system` events on rate limits or API errors.

```python
from hilt.io.session import Session
from hilt.integrations.openai import (
    log_chat_completion,
    log_chat_streaming,
    log_rag_interaction,
)

with Session("logs/openai.hilt.jsonl") as session:
    log_chat_completion(session, user_message="Translate hello to Spanish")
    log_chat_streaming(session, user_message="Explain quantum computing briefly")

with Session("logs/rag.hilt.jsonl") as session:
    log_rag_interaction(
        session,
        user_message="What is alpha?",
        answer="Alpha is…",
        retrieved_documents=[{"id": "doc-1", "text": "Alpha doc"}],
    )
```

- `log_chat_completion` enregistre prompt + réponse + métriques (latence, tokens, coûts, statut).
- `log_chat_streaming` crée des événements `completion_chunk` pour chaque delta, agrège la réponse finale et conserve les métriques complètes.
- `log_rag_interaction` relie prompt, documents récupérés (`retrieval`) et réponse finale (`completion`) avec références (`reply_to`), scores et coûts calculés lorsque les tokens sont fournis.

Voir `examples/openai_integration.py` pour un script complet avec affichage et conversion CSV.

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

## REST API Example

Ship a minimal chatbot API using the FastAPI stack bundled in the `api` extra.

```bash
pip install "hilt[api]"
python examples/chatbot_api.py
```

The example stores conversations in `logs/chatbot.hilt.jsonl`, exposes a `/chat` endpoint, and streams metrics that work with the Google Sheets backend.

## Custom Integrations

When writing your own adapters:

1. Capture request/response payloads.
2. Construct `Event` instances that include metrics and metadata.
3. Use `Session` to append events.
4. Add provenance (`event.provenance`) for audit trails (e.g., model IDs, request IDs).

For inspiration, inspect `hilt/integrations/langchain.py` and `hilt/integrations/anthropic.py`.
