# Google Sheets Setup

Follow these steps to enable the Sheets backend for HILT logging.

## 1. Create a service account

1. Visit the [Google Cloud Console](https://console.cloud.google.com/).
2. Create (or reuse) a project for your logging setup.
3. Navigate to **IAM & Admin → Service Accounts**.
4. Click **Create Service Account**, give it a name, and finish the creation.
5. After creation, open the service account and generate a JSON key:
   - Go to the **Keys** tab, click **Add key → Create new key**.
   - Choose **JSON** and download the file (e.g., `credentials.json`).

> Keep this file private—it grants access to your Google Sheets.

## 2. Enable the Google Sheets API

1. In the same project, visit **APIs & Services → Library**.
2. Search for "Google Sheets API" and click **Enable**.
3. (Optional) Enable the Google Drive API if you plan to create sheets programmatically.

## 3. Share your sheet with the service account

1. Open the downloaded `credentials.json` file and copy the value under `client_email`.
2. Open the Google Sheet you want to use for logging.
3. Click **Share**, paste the `client_email` into the people picker (Add people/share field), and invite that service account.
4. Grant at least **Editor** access so HILT can append rows.

## 4. Retrieve the Sheet ID

The Sheet ID is the long string in the sheet’s URL:

```
https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit
```

Copy the value between `/d/` and `/edit`—that’s the ID you pass to HILT.

## 5. Configure HILT

Set environment variables (recommended):

```bash
export GOOGLE_SHEET_ID=""
export GOOGLE_CREDENTIALS_PATH="/path/to/credentials.json"
```

Or load credentials directly in code:

```python
from hilt import instrument

instrument(
    backend="sheets",
    sheet_id="",
    credentials_path="/path/to/credentials.json"
)
```

## 6. Verify access

Run a quick script to ensure everything works:

```python
from hilt import instrument

instrument(backend="sheets", sheet_id="YOUR_SHEET_ID", credentials_path="credentials.json")
print("✅ Sheets instrumentation active")
```

If you see errors, double-check the sheet sharing permissions and the credential file path.

## Helpful tips

- Store `credentials.json` outside your repo and reference it via an environment variable.
- For multi-environment setups, keep separate sheets (or worksheets) per environment.
- Rotate keys periodically via the Google Cloud Console for better security.

