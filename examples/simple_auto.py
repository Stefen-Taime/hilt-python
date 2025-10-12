"""
HILT Auto-Instrumentation - Simple Example

Shows how to automatically log all LLM calls with one line of code.
"""

import os


def main():
    """Demonstrate HILT auto-instrumentation."""
    
    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not set")
        print("   Run: export OPENAI_API_KEY='sk-...'")
        return
    
    print("\n🔥 HILT Auto-Instrumentation Demo\n")
    print("=" * 60)
    
    # 🚀 Enable auto-logging (ONE LINE!)
    from hilt import instrument
    instrument(backend="local", filepath="logs/simple.jsonl")
    
    # ✨ Your existing code works unchanged
    from openai import OpenAI
    
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say 'HILT rocks!' in French"}]
    )
    
    print(f"\n🤖 Response: {response.choices[0].message.content}")
    print("\n✅ Automatically logged with full metrics!")
    print("📁 Check: logs/simple.jsonl\n")
    


if __name__ == "__main__":
    main()