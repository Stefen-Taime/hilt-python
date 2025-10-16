# Installation

Get HILT up and running in a couple of minutes.

## Requirements

- Python 3.10 or newer (matches the package metadata)
- An OpenAI API key if you plan to call the OpenAI SDK
- A virtual environment (venv/poetry) is recommended

## Install from PyPI

```bash
pip install hilt-python
```

This installs the core package, including the OpenAI SDK dependency that the instrumentor patches.

## Optional: Google Sheets support

For real-time dashboards, install the Sheets extra:

```bash
pip install "hilt-python[sheets]"
```

Then either set environment variables:

```bash
export GOOGLE_SHEET_ID="1nduXlCD47mU2TiCJDgr29_K9wFg_vi1DpvflFsTHM44"
export GOOGLE_CREDENTIALS_PATH="credentials.json"
```

Or pass credentials directly in code:

```python
from hilt import instrument

instrument(
    backend="sheets",
    sheet_id="...",
    credentials_path="credentials.json",
)
```

Steps to prepare the credentials:

1. Create a Google Cloud service account.
2. Enable the Google Sheets API.
3. Download the JSON credentials file.
4. Share your target Google Sheet with the service account email.

## Verify installation

```python
from hilt import instrument

instrument  # noqa: silences unused warning in quick REPL checks
print("✅ HILT installed successfully!")
```

## Set up OpenAI

```bash
export OPENAI_API_KEY="sk-..."  # macOS/Linux
```

On Windows PowerShell:

```powershell
$env:OPENAI_API_KEY="sk-..."
```

Or inside Python:

```python
import os
os.environ["OPENAI_API_KEY"] = "sk-..."
```

## Install from source

```bash
git clone https://github.com/Stefen-Taime/hilt-python.git
cd hilt-python
poetry install --with dev
```

Run tests to double-check the environment:

```bash
poetry run pytest
```

## Quick test script

Create `test_hilt.py`:

```python
"""Quick sanity check for HILT auto-instrumentation."""

import os
from hilt import instrument
from openai import OpenAI

if not os.getenv("OPENAI_API_KEY"):
    raise SystemExit("Set OPENAI_API_KEY before running this script.")

instrument(backend="local", filepath="logs/test.jsonl")

client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Say 'HILT works!'"}],
)

print(response.choices[0].message.content)
print("✅ Check logs/test.jsonl for the recorded events.")
```

Run it with:

```bash
python test_hilt.py
```

## Upgrade or remove

```bash
pip install --upgrade hilt-python
pip install --upgrade "hilt-python[sheets]"  # if you use the Sheets extra
pip uninstall hilt-python                 # to remove the package
```

## Troubleshooting

**`ImportError: No module named 'hilt'`**  
Ensure you are inside the correct virtual environment and the package is installed (`pip list | grep hilt-python`).

**Google Sheets backend not working**  
Install the Sheets extra (`pip install "hilt-python[sheets]"`) and confirm `gspread` appears in `pip list`.

**Poetry installation issues**  
Update Poetry (`pip install --upgrade poetry`), clear the cache (`poetry cache clear . --all`), and retry `poetry install`.

## Next steps

- [Quickstart](quickstart.md) – instrument, call OpenAI, inspect logs
- [Integrations](integrations.md) – provider-specific behaviour and roadmap
- [API reference](api.md) – deep dive into sessions and data models
