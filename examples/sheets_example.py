"""Test HILT with custom Google Sheets columns."""

import os
from hilt import instrument
from openai import OpenAI

if not os.getenv("OPENAI_API_KEY") or not os.getenv("GOOGLE_SHEET_ID"):
    print("❌ Missing credentials")
    exit(1)

# Custom columns - choisissez uniquement celles dont vous avez besoin
instrument(
    backend="sheets",
    sheet_id=os.getenv("GOOGLE_SHEET_ID"),
    credentials_path="credentials.json",
    worksheet_name="Custom View",
    columns=[
        'timestamp',
        'conversation_id',
        'reply_to',
        'message',
        'cost_usd',
        'status_code'
    ]
)

client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "What is 2+2?"}]
)

print(response.choices[0].message.content)