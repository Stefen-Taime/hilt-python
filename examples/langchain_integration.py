"""Example demonstrating the HILT LangChain callback handler."""

from __future__ import annotations

import json

from langchain.schema import LLMResult, Generation

from hilt.io.session import Session
from hilt.integrations.langchain import HILTCallbackHandler


def main() -> None:
    session_path = "logs/langchain.hilt.jsonl"
    with Session(session_path) as session:
        callback = HILTCallbackHandler(session, session_id="example-session")

        # Simulate a LangChain LLM call by invoking callbacks directly.
        callback.on_chain_start({"name": "example"}, {}, run_id="chain")
        callback.on_llm_start({"name": "demo-llm"}, ["What is the capital of France?"], run_id="llm", parent_run_id="chain")
        result = LLMResult(generations=[[Generation(text="The capital is Paris.")]])
        result.llm_output = {
            "token_usage": {
                "prompt_tokens": 12,
                "completion_tokens": 18,
                "total_tokens": 30,
            },
            "model_name": "gpt-3.5-turbo",
        }
        callback.on_llm_end(result, run_id="llm", parent_run_id="chain")
        callback.on_chain_end({"output": "done"}, run_id="chain")

    print(f"Events written to {session_path}")
    with open(session_path, "r", encoding="utf-8") as handle:
        for line in handle:
            print(json.loads(line))


if __name__ == "__main__":
    main()
