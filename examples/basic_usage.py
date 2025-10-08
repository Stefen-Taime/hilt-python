"""
Basic HILT usage example.

This example demonstrates:
1. Creating a session
2. Logging events
3. Reading events back
"""

from hilt import Session, Event, Actor, Content, Metrics

def main():
    print("🚀 HILT Basic Usage Example\n")
    
    # Create a session for logging
    filepath = "logs/example.hilt.jsonl"
    
    print(f"📝 Writing events to: {filepath}")
    
    # Write some events
    with Session(filepath, mode="w") as session:
        # Event 1: User prompt
        event1 = Event(
            session_id="sess_demo_123",
            actor=Actor(type="human", id="alice"),
            action="prompt",
            content=Content(text="What is the capital of France?")
        )
        session.append(event1)
        print(f"✅ Logged: {event1.actor.id} - {event1.action}")
        
        # Event 2: AI completion
        event2 = Event(
            session_id="sess_demo_123",
            actor=Actor(type="agent", id="gpt-4"),
            action="completion",
            content=Content(text="The capital of France is Paris."),
            metrics=Metrics(
                latency_ms=1234,
                tokens={"prompt": 10, "completion": 8, "total": 18},
                cost_usd=0.00054
            )
        )
        session.append(event2)
        print(f"✅ Logged: {event2.actor.id} - {event2.action}")
        
        # Event 3: Another prompt
        event3 = Event(
            session_id="sess_demo_123",
            actor=Actor(type="human", id="alice"),
            action="prompt",
            content=Content(text="What about Germany?")
        )
        session.append(event3)
        print(f"✅ Logged: {event3.actor.id} - {event3.action}")
    
    print(f"\n📖 Reading events from: {filepath}\n")
    
    # Read events back
    session = Session(filepath, mode="r")
    for i, event in enumerate(session.read(), start=1):
        print(f"Event {i}:")
        print(f"  ID: {event.event_id}")
        print(f"  Time: {event.timestamp}")
        print(f"  Actor: {event.actor.type} ({event.actor.id})")
        print(f"  Action: {event.action}")
        if event.content and event.content.text:
            print(f"  Text: {event.content.text}")
        if event.metrics:
            print(f"  Metrics: {event.metrics}")
        print()
    
    print("✅ Example completed successfully!")

if __name__ == "__main__":
    main()