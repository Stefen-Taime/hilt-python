# Quickstart

Get productive with HILT in under five minutes.

## Table of Contents

1. [Create an Event](#create-an-event)
2. [Write to a Session](#write-to-a-session)
3. [Read Events Back](#read-events-back)
4. [Convert to CSV](#convert-to-csv)
5. [Next Steps](#next-steps)

## Create an Event

```python
from hilt import Event, Actor, Content

event = Event(
    session_id="quickstart-session",
    actor=Actor(type="human", id="user-123"),
    action="prompt",
    content=Content(text="Summarise the HILT project.")
)
```

## Write to a Session

```python
from hilt import Session

with Session("logs/quickstart.hilt.jsonl") as session:
    session.append(event)
```

This stores each event as a JSON line in `logs/quickstart.hilt.jsonl`.

Need collaborative logging? Install the `sheets` extra and switch the backend:

```python
with Session(
    backend="sheets",
    sheet_id="YOUR_SHEET_ID",
    credentials_path="service-account.json",
    columns=["timestamp", "speaker", "message", "tokens_out", "cost_usd"],
) as session:
    session.append(event)
```

## Read Events Back

```python
reader = Session("logs/quickstart.hilt.jsonl", mode="r")
events = list(reader.read())

print(len(events))            # -> 1
print(events[0].content.text) # -> "Summarise the HILT project."
```

## Convert to CSV

```python
from hilt.converters.csv import convert_to_csv

convert_to_csv(
    input_file="logs/quickstart.hilt.jsonl",
    output_file="logs/quickstart.csv"
)
```

Open the resulting CSV in Excel, Google Sheets, or any analytics pipeline.

## Next Steps

- Explore the [CLI guide](cli.md) for automated validation and stats.
- Dive into the [API reference](api.md) for advanced usage.
- Integrate with LangChain, OpenAI, or Anthropic via [Integrations](integrations.md).
