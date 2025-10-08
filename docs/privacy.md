# Privacy & Compliance

Responsible logging is a first-class requirement for HILT. This guide covers PII handling, encryption, GDPR alignment, and best practices.

## Table of Contents

1. [PII Handling](#pii-handling)
2. [Encryption & Hashing](#encryption--hashing)
3. [GDPR Compliance](#gdpr-compliance)
4. [Best Practices](#best-practices)

## PII Handling

- Use `Privacy.pii_detected` to list sensitive attributes (emails, phone numbers, etc.).
- Toggle `Privacy.redaction_applied` when redactions occur upstream.
- Store consent artifacts (checkbox state, privacy notices) in `Privacy.consent`.
- Prefer hashed or tokenized identifiers via `hilt.utils.hash_content`.

## Encryption & Hashing

- Encrypt payloads before writing to disk and store ciphertext in `Content.text_encrypted`.
- Use `Content.text_hash` for integrity checks (e.g., SHA-256 digest).
- Sign entire events via `Event.integrity` to maintain tamper-evident logs.

Example hashing flow:

```python
from hilt import Content
from hilt.utils import hash_content

content = Content(text_hash=hash_content("Sensitive message"))
```

## GDPR Compliance

HILT provides structure, but compliance depends on how you use it:

- **Purpose limitation:** store `provenance` indicating why data was collected.
- **Data minimization:** log only necessary fields, leverage `extensions` sparingly.
- **Subject access:** events are easily exportable via CSV/Parquet.
- **Retention policies:** rotate JSONL files and implement archival/deletion scripts.

## Best Practices

- Rotate sessions per user or conversation to simplify deletions.
- Store secrets (API keys, tokens) outside the log file.
- Automate PII detection with upstream policies, flag results in `Privacy`.
- Leverage CLI validation in CI to enforce schema correctness before shipping logs.
