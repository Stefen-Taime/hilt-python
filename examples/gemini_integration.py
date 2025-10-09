"""Example: log Google Gemini interactions with HILT."""

from __future__ import annotations

import json

from hilt.integrations.gemini import log_gemini_interaction
from hilt.io.session import Session


def main() -> None:
    session_path = "logs/gemini.hilt.jsonl"
    prompt = "Give me three bullet points about renewable energy."
    response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "- Solar power\n- Wind energy\n- Hydroelectric generation"}
                    ]
                }
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 18,
            "candidatesTokenCount": 24,
            "totalTokenCount": 42,
        },
    }

    with Session(session_path) as session:
        log_gemini_interaction(
            session,
            user_message=prompt,
            response=response,
            session_id="gemini_demo",
            user_id="demo-user",
            assistant_id="gemini-1.5-pro",
        )

    print(f"Gemini interaction logged to {session_path}")
    with open(session_path, "r", encoding="utf-8") as handle:
        for line in handle:
            print(json.loads(line))


if __name__ == "__main__":
    main()
