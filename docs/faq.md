# FAQ

Common questions and troubleshooting tips.

## Table of Contents

1. [General](#general)
2. [Troubleshooting](#troubleshooting)
3. [Comparisons](#comparisons)

## General

### Why JSONL?

JSONL (JSON Lines) is human-readable, append-friendly, and plays well with big data tooling. Each HILT event is a single JSON object per line.

### Is HILT schema-free?

Events are validated using Pydantic models (`Event`, `Actor`, `Metrics`, etc.), offering both structure and extensibility via `extensions` and `provenance`.

### How do I rotate logs?

Use one JSONL file per day or session. The CLI supports conversion and stats on each shard.

### Can I control which fields appear in Google Sheets?

Yes. When you construct `Session(backend="sheets", ...)`, pass a `columns=[...]` list to choose and order the available fields (e.g., `"timestamp"`, `"message"`, `"tokens_out"`, `"cost_usd"`). Any omitted columns are hidden from the sheet.

## Troubleshooting

### `hilt validate` reports invalid JSON

Ensure each line is a valid JSON object. Use streaming writers that flush complete lines and avoid manual concatenation errors.

### Parquet conversion fails with `ImportError`

Install the optional dependency:

```bash
pip install "hilt[parquet]"
```

### Google Sheets backend raises `ImportError`

Install the Sheets extras and provide credentials:

```bash
pip install "hilt[sheets]"
```

Then pass `backend="sheets"` along with `sheet_id` and `credentials_path` when constructing the session.

### LangChain callbacks are not logged

Install extras (`hilt[langchain]`) and pass the handler in `callbacks=[...]`. Ensure `include_metrics=True` if you expect usage data.

### CLI commands run out of memory on large files

The converters stream and should not load entire files. For stats, consider splitting logs per day or using Parquet for analytics.

## Comparisons

| Feature               | HILT                  | Custom JSON | CSV Only |
|-----------------------|-----------------------|-------------|----------|
| Schema validation     | ✅ (Pydantic)         | ❌          | ❌       |
| Nested data           | ✅                    | ✅          | 🚫       |
| Extensibility         | ✅ (`extensions`)     | ✅          | 🚫       |
| Analytics friendly    | ✅ (CSV/Parquet)      | ⚠️ manual   | ✅       |
| Privacy metadata      | ✅ (`Privacy` fields) | ❌          | ❌       |

Need more help? Open an issue on GitHub or join the community discussions.
