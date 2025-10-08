"""Example: log Anthropic Claude conversations with HILT."""

from __future__ import annotations

import json

from hilt.integrations.anthropic import log_claude_interaction
from hilt.io.session import Session


def main() -> None:
    session_path = "logs/claude.hilt.jsonl"
    user_message = "Give me a short haiku about the ocean."
    response = {
        "content": [{"text": "Endless blue horizon\nWaves whisper ancient secrets\nSky kisses the sea"}],
        "usage": {"input_tokens": 12, "output_tokens": 28, "total_tokens": 40},
    }

    with Session(session_path) as session:
        log_claude_interaction(
            session,
            user_message=user_message,
            response=response,
            session_id="claude_demo",
            user_id="demo-user",
            assistant_id="claude-3-opus",
        )

    print(f"Claude interaction logged to {session_path}")
    with open(session_path, "r", encoding="utf-8") as handle:
        for line in handle:
            print(json.loads(line))


if __name__ == "__main__":
    main()
