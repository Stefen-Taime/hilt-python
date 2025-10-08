"""
OpenAI integration example.

This example shows how to log OpenAI API calls with HILT.
Note: You need to install openai package and set OPENAI_API_KEY
"""

from hilt import Session, Event, Actor, Content, Metrics

def log_openai_call(session: Session, user_message: str, assistant_message: str, usage: dict):
    """
    Log an OpenAI conversation to HILT.
    
    Args:
        session: HILT session
        user_message: User's message
        assistant_message: Assistant's response
        usage: Token usage from OpenAI response
    """
    # Log user prompt
    prompt_event = Event(
        session_id="openai_session",
        actor=Actor(type="human", id="user_001"),
        action="prompt",
        content=Content(text=user_message)
    )
    session.append(prompt_event)
    
    # Log AI completion
    completion_event = Event(
        session_id="openai_session",
        actor=Actor(type="agent", id="gpt-4"),
        action="completion",
        content=Content(text=assistant_message),
        metrics=Metrics(
            tokens={
                "prompt": usage.get("prompt_tokens", 0),
                "completion": usage.get("completion_tokens", 0),
                "total": usage.get("total_tokens", 0)
            },
            cost_usd=usage.get("total_tokens", 0) * 0.00003  # Approximate
        )
    )
    session.append(completion_event)

def main():
    """Example of logging OpenAI conversations."""
    print("🤖 OpenAI + HILT Integration Example\n")
    
    # Simulated OpenAI call (replace with real API call)
    user_message = "Explain quantum computing in simple terms"
    assistant_message = "Quantum computing uses quantum bits (qubits) that can be in multiple states..."
    usage = {
        "prompt_tokens": 15,
        "completion_tokens": 50,
        "total_tokens": 65
    }
    
    # Log to HILT
    with Session("logs/openai.hilt.jsonl") as session:
        log_openai_call(session, user_message, assistant_message, usage)
    
    print("✅ OpenAI conversation logged successfully!")
    print(f"📁 Check logs/openai.hilt.jsonl for details")

if __name__ == "__main__":
    main()