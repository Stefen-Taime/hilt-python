# Privacy & Compliance

Auto-instrumentation makes it effortless to log prompts and completions, which also means sensitive data may flow into your telemetry. Use the guardrails below to keep HILT compliant with privacy requirements—no CLI tooling required.

## Capture only what you need

- **Sanitise before logging.** Apply redaction or masking before content reaches the model or the log.
- **Prefer local storage for PII-heavy workloads.** Use the JSONL backend when you control disk encryption and access policies.
- **Restrict Google Sheets exposure.** If you need collaborative dashboards, limit the columns you publish:

```python
from hilt import instrument

instrument(
    backend="sheets",
    sheet_id="...",
    columns=["timestamp", "action", "cost_usd", "status_code"],  # No message content
)
```

- **Pause logging for sensitive flows.** Wrap protected actions with `uninstrument()` / `instrument()` to ensure they are not recorded.

```python
from hilt import instrument, uninstrument

instrument(backend="local", filepath="logs/app.jsonl")
# ... normal operations
uninstrument()  # Temporarily disable for a sensitive operation
instrument(backend="local", filepath="logs/app.jsonl")  # Re-enable afterwards
```

## Track privacy signals in events

HILT’s schema lets you embed privacy metadata directly inside `extensions`:

```python
from hilt import Event

event = Event(
    session_id="conv_xyz",
    actor={"type": "human", "id": "user-123"},
    action="prompt",
    content={"text": "[REDACTED]"},
    extensions={
        "privacy": {
            "pii_detected": ["email_address", "phone_number"],
            "redaction_applied": True,
            "consent": {
                "source": "web-form",
                "version": "2025-01",
                "granted": True,
            },
        }
    },
)
```

## Redaction strategies

### Option 1: Pre-processing (recommended)

Redact input before sending it to the LLM so sensitive data never leaves your system.

```python
import re
from openai import OpenAI
from hilt import instrument

instrument(backend="local", filepath="logs/app.jsonl")
client = OpenAI()

def redact_email(text: str) -> str:
    pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    return re.sub(pattern, "[EMAIL]", text)

user_input = "My email is john@example.com"
sanitised_input = redact_email(user_input)

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": sanitised_input}],
)
```

### Option 2: Post-processing

Scan existing logs and redact or delete records as needed.

```python
from hilt import Session

with Session("logs/app.jsonl", mode="r") as session:
    for event in session.read():
        text = event.content.text if event.content and event.content.text else ""
        if "password" in text.lower():
            # Trigger alert, redact content, or remove event
            pass
```

## Hashing and encryption

Hash or encrypt identifiers before storage when regulations require irreversible tokens.

```python
import hashlib
from hilt import Event

user_id = "user-12345"
hashed_id = hashlib.sha256(user_id.encode()).hexdigest()

event = Event(
    session_id="conv_abc",
    actor={"type": "human", "id": hashed_id},
    action="prompt",
    content={"text": "Query content"},
    extensions={
        "integrity": {
            "user_hash": hashed_id,
            "hash_algorithm": "sha256",
        }
    },
)
```

Keep encryption keys outside of the logs themselves (for example, managed by your secrets manager).

## Data subject rights (GDPR, CCPA)

### Access requests

Export a user’s data with the Session reader:

```python
import json
from hilt import Session

def export_user_data(user_id: str, output_file: str) -> None:
    with Session("logs/app.jsonl", mode="r") as session:
        user_events = [
            event.to_dict()
            for event in session.read()
            if event.actor.id == user_id
        ]

    with open(output_file, "w", encoding="utf-8") as handle:
        json.dump(user_events, handle, indent=2)
```

### Deletion requests

Rewrite logs without the user’s data:

```python
from hilt import Session

def delete_user_data(user_id: str, input_file: str, output_file: str) -> None:
    with Session(input_file, mode="r") as read_session:
        with Session(output_file, mode="w") as write_session:
            for event in read_session.read():
                if event.actor.id != user_id:
                    write_session.append(event)
```

### Conversation-level deletion

Remove an entire conversation by session ID:

```python
from hilt import Session

def delete_conversation(conversation_id: str, input_file: str, output_file: str) -> None:
    with Session(input_file, mode="r") as read_session:
        with Session(output_file, mode="w") as write_session:
            for event in read_session.read():
                if event.session_id != conversation_id:
                    write_session.append(event)
```

## Governance tips

### Data retention

**Local backend**

- Rotate JSONL files daily or weekly (e.g., `logs/chat-2025-10-12.jsonl`).
- Automate deletion of old files:

```python
from pathlib import Path
from datetime import datetime, timedelta

def cleanup_old_logs(logs_dir: str, days: int = 30) -> None:
    cutoff = datetime.now() - timedelta(days=days)
    for log_file in Path(logs_dir).glob("*.jsonl"):
        if log_file.stat().st_mtime < cutoff.timestamp():
            log_file.unlink()
            print(f"Deleted old log: {log_file}")
```

**Google Sheets backend**

- Configure spreadsheet-level retention policies.
- Schedule exports to long-term storage, then purge old rows.

### Access control

- Lock down local log directories:

```bash
chmod 700 logs/
chown app-user:app-user logs/
```

- For Google Sheets, share only with the service account or read-only viewers and review sharing settings regularly.

### Compliance documentation

Maintain an internal policy describing:

- **What data is logged** (prompts, completions, metrics—avoid raw PII)
- **Where it is stored** (local path or Google Sheets URL)
- **Retention periods** (e.g., production 30 days, audit logs 1 year)
- **Who has access** (engineering, support, compliance teams)
- **Data subject processes** (export and deletion scripts, SLA timelines)

### Audit trail

Log human actions alongside automated events to preserve provenance.

```python
from hilt import Event

audit_event = Event(
    session_id="audit_log",
    actor={"type": "human", "id": "admin-456"},
    action="data_export",
    content={"text": "Exported data for user user-123"},
    extensions={
        "audit": {
            "action": "gdpr_export",
            "target_user": "user-123",
            "requestor": "admin-456",
            "reason": "User access request",
        }
    },
)
```

## Best practices summary

✅ **Do**

- Use the local backend for sensitive workloads
- Redact or hash PII before it reaches the LLM
- Document retention and access control policies
- Implement export/deletion workflows for subject rights
- Review Google Sheets sharing permissions regularly

❌ **Don’t**

- Log secrets, passwords, or API keys
- Share dashboards publicly
- Keep logs indefinitely
- Ignore user data requests
- Mix regulated data with open analytics datasets

## Need help?

- Check the rest of the documentation for advanced usage and API details
- Open an issue on GitHub for implementation questions or compliance concerns
