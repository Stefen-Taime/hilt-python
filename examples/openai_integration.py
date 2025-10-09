"""Example: log OpenAI GPT interactions to HILT."""

from __future__ import annotations

import os

from openai import OpenAI, OpenAIError, RateLimitError

from hilt import Actor, Content, Event, Metrics, Session


def log_openai_call(
    session: Session,
    *,
    user_message: str,
    session_id: str = "openai_session",
    user_id: str = "user",
    assistant_id: str = "gpt-4o-mini",
) -> None:
    """Call OpenAI ChatCompletions API and persist the interaction."""

    client = OpenAI()

    session.append(
        Event(
            session_id=session_id,
            actor=Actor(type="human", id=user_id),
            action="prompt",
            content=Content(text=user_message),
        )
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": user_message}],
        )
        assistant_message = response.choices[0].message["content"]
        usage = response.usage or {}

        session.append(
            Event(
                session_id=session_id,
                actor=Actor(type="agent", id=assistant_id),
                action="completion",
                content=Content(text=assistant_message),
                metrics=Metrics(
                    tokens={
                        "prompt": usage.get("prompt_tokens", 0),
                        "completion": usage.get("completion_tokens", 0),
                        "total": usage.get("total_tokens", 0),
                    },
                ),
            )
        )

    except RateLimitError as error:
        session.append(
            Event(
                session_id=session_id,
                actor=Actor(type="system", id="openai"),
                action="system",
                content=Content(text=f"Rate limit reached: {error}"),
                extensions={"error_code": "rate_limit"},
            )
        )
        raise

    except OpenAIError as error:
        session.append(
            Event(
                session_id=session_id,
                actor=Actor(type="system", id="openai"),
                action="system",
                content=Content(text=f"OpenAI error: {error}"),
                extensions={"error_code": "api_error"},
            )
        )
        raise


def main() -> None:
    print("🤖 OpenAI + HILT Integration Example\n")

    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Set OPENAI_API_KEY before running this example.")
        return

    user_message = "Explain quantum computing in simple terms"

    try:
        with Session("logs/openai.hilt.jsonl") as session:
            log_openai_call(session, user_message=user_message)
        print("✅ Interaction logged to logs/openai.hilt.jsonl")
    except RateLimitError:
        print("❌ Rate limit exceeded; error recorded in HILT session.")
    except OpenAIError as error:
        print(f"❌ OpenAI API error: {error}; details recorded in HILT session.")


if __name__ == "__main__":
    main()
