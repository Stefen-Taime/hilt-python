# FAQ

Common questions about HILT auto-instrumentation.

## General

### Do I need to change my existing OpenAI code?

**No.** Just call `instrument()` once at startup and your existing code works unchanged:

```python
from hilt import instrument

instrument(backend="local", filepath="logs/app.jsonl")

# Rest of your code stays the same
from openai import OpenAI
client = OpenAI()
response = client.chat.completions.create(...)
```

HILT transparently wraps the OpenAI SDK and leaves response objects untouched.

### How do I stop instrumentation?

Call `uninstrument()` to restore the original SDK:

```python
from hilt import uninstrument

uninstrument()
# Logging is now disabled
```

This also closes the active session so no events remain buffered.

### Where are logs stored?

**Local backend (default):**

- Newline-delimited JSON (`.jsonl`) files
- Privacy-first—data never leaves your environment
- Example path: `logs/app.jsonl`

**Google Sheets backend (optional):**

- Real-time updates to a Google Sheet
- Ideal for team dashboards and cost monitoring
- Requires `pip install "hilt[sheets]"`

```python
# Local
instrument(backend="local", filepath="logs/app.jsonl")

# Google Sheets
instrument(backend="sheets", sheet_id="...")
```

### Can I log custom events?

Yes. Access the active session and append events manually:

```python
from hilt import Event
from hilt.instrumentation import get_context

session = get_context().session

session.append(
    Event(
        session_id="conv_abc",
        actor={"type": "tool", "id": "vector-db"},
        action="retrieval",
        content={"text": "Retrieved document..."},
    )
)
```

Great for tool calls, human feedback, guardrail results, or custom metrics.

### Does HILT work with async code?

Yes. HILT is thread-safe and compatible with async frameworks.

```python
import asyncio
from hilt import instrument
from openai import AsyncOpenAI

instrument(backend="local", filepath="logs/async.jsonl")

async def main():
    client = AsyncOpenAI()
    response = await client.chat.completions.create(...)
    # ✅ Logged automatically

asyncio.run(main())
```

### Are other providers supported?

Not yet. Today HILT only instruments the official OpenAI Python SDK. If you want to help add additional providers, open an issue or pull request on GitHub.

### Can I use HILT in production?

Yes. HILT is production-ready:

- ✅ Thread-safe
- ✅ Minimal overhead
- ✅ Built-in error handling
- ✅ No third-party data sharing (local backend)

Production tips:

- Use the local backend for sensitive data
- Rotate log files daily
- Monitor disk usage
- Establish log retention policies

## Troubleshooting

### Nothing is being logged

**1. Check import order**

```python
# ✅ Correct
from hilt import instrument
instrument(...)
from openai import OpenAI

# ❌ Incorrect
from openai import OpenAI
from hilt import instrument
instrument(...)  # Too late!
```

**2. Verify the API key**

```bash
echo $OPENAI_API_KEY
```

Set it if missing.

**3. Confirm file permissions**

```bash
ls -la logs/
```

**4. Verify instrumentation is active**

```python
from hilt.instrumentation import get_context

context = get_context()
print(f"Instrumented: {context.is_instrumented}")
print(f"Session: {context.session}")
```

### Google Sheets writes fail

1. Install the Sheets extra:

```bash
pip install "hilt[sheets]"
pip list | grep gspread
```

2. Share the sheet with the service account email (found in `credentials.json`):

```bash
cat credentials.json | grep client_email
```

3. Ensure credentials are configured:

```python
import os

print(os.getenv("GOOGLE_SHEET_ID"))
print(os.getenv("GOOGLE_CREDENTIALS_PATH"))
```

4. Test the credentials manually:

```python
import gspread
from google.oauth2.service_account import Credentials

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
client = gspread.authorize(creds)
sheet = client.open_by_key("YOUR_SHEET_ID")
print(f"✅ Connected to: {sheet.title}")
```

### Logs are huge / disk space issues

Rotate logs by date:

```python
from datetime import datetime
from hilt import instrument

date_str = datetime.now().strftime("%Y-%m-%d")
instrument(backend="local", filepath=f"logs/app-{date_str}.jsonl")
```

Cleanup script:

```python
from pathlib import Path
from datetime import datetime, timedelta

def cleanup_old_logs(logs_dir="logs", days=30):
    cutoff = datetime.now() - timedelta(days=days)
    for log_file in Path(logs_dir).glob("*.jsonl"):
        if log_file.stat().st_mtime < cutoff.timestamp():
            log_file.unlink()
            print(f"Deleted: {log_file}")

cleanup_old_logs()
```

### Performance concerns

**Q:** Does HILT slow down my API calls?  
**A:** Overhead is minimal (~1–2 ms per call) because logging is lightweight and uses append-only writes.

Basic benchmark:

```python
import time
from hilt import instrument
from openai import OpenAI

instrument(backend="local", filepath="logs/bench.jsonl")
client = OpenAI()

start = time.time()
for _ in range(100):
    client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hi"}],
    )
end = time.time()

print(f"Average overhead: {(end - start) / 100 * 1000:.2f} ms per call")
```

## Best practices

**Log rotation**

```python
from datetime import datetime

date = datetime.now().strftime("%Y-%m-%d")
instrument(backend="local", filepath=f"logs/app-{date}.jsonl")
```

**Privacy**

```python
import re

def redact_email(text: str) -> str:
    pattern = r"\b[\w\.-]+@[\w\.-]+\.\w+\b"
    return re.sub(pattern, "[EMAIL]", text)

user_input = redact_email(user_input)
```

See the Privacy guide for more ideas.

**Monitoring**

```python
from hilt import Session

total_cost = 0.0
error_count = 0

with Session("logs/prod.jsonl", mode="r") as session:
    for event in session.read():
        if event.metrics and event.metrics.cost_usd:
            total_cost += event.metrics.cost_usd
        status = event.extensions.get("status_code") if event.extensions else None
        if status and status >= 400:
            error_count += 1

print(f"Total cost: ${total_cost:.4f}")
print(f"Errors: {error_count}")
```

**Production setup**

```python
import os
from hilt import instrument

env = os.getenv("ENVIRONMENT", "development")

if env == "production":
    instrument(
        backend="sheets",
        sheet_id=os.getenv("GOOGLE_SHEET_ID"),
        credentials_path="credentials.json",
    )
else:
    instrument(backend="local", filepath=f"logs/{env}.jsonl")
```

## Still need help?

- 📖 Browse the rest of the documentation
- 🐛 Report an issue on GitHub
- 💬 Join discussions (coming soon)
