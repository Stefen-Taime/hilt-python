"""LangChain callback handler that records events in HILT sessions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

try:
    from langchain.callbacks.base import BaseCallbackHandler
except ImportError as exc:  # pragma: no cover - optional dependency
    raise ImportError(
        "LangChain is required for the HILT LangChain integration. Install the 'hilt[langchain]' extra."
    ) from exc

from hilt.core.event import Event
from hilt.io.session import Session
from hilt.utils.uuid import generate_event_id


@dataclass
class _LLMMetrics:
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_usd: Optional[float] = None


class HILTCallbackHandler(BaseCallbackHandler):
    """LangChain callback handler that logs interactions to a HILT session."""

    def __init__(
        self,
        session: Session,
        session_id: Optional[str] = None,
        include_metrics: bool = True,
    ) -> None:
        self.session = session
        self.default_session_id = session_id or f"langchain-{generate_event_id()}"
        self.include_metrics = include_metrics
        self._chain_sessions: Dict[str, str] = {}
        self._tool_names: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Chain lifecycle
    # ------------------------------------------------------------------
    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any) -> None:
        run_id = kwargs.get("run_id")
        metadata = kwargs.get("metadata") or {}
        session_id = metadata.get("session_id") or self.default_session_id
        if run_id:
            self._chain_sessions[run_id] = session_id
        name = serialized.get("name") or metadata.get("name") or "chain"
        self._append_event(
            session_id=session_id,
            action="system",
            actor_type="system",
            actor_id=name,
            content=f"Chain started with inputs: {inputs}",
            provenance={"langchain": {"run_id": run_id, "metadata": metadata}},
        )

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        run_id = kwargs.get("run_id")
        session_id = self._resolve_session_id(run_id=run_id)
        name = "chain"
        if run_id and run_id in self._chain_sessions:
            name = self._chain_sessions[run_id]
        self._append_event(
            session_id=session_id,
            action="system",
            actor_type="system",
            actor_id=name,
            content=f"Chain completed with outputs: {outputs}",
            provenance={"langchain": {"run_id": run_id}},
        )
        if run_id and run_id in self._chain_sessions:
            self._chain_sessions.pop(run_id, None)

    # ------------------------------------------------------------------
    # LLM callbacks
    # ------------------------------------------------------------------
    def on_llm_start(self, serialized: Dict[str, Any], prompts: Iterable[str], **kwargs: Any) -> None:
        run_id = kwargs.get("run_id")
        parent_run_id = kwargs.get("parent_run_id")
        session_id = self._resolve_session_id(run_id=parent_run_id)
        actor_id = serialized.get("name") or "llm"
        for prompt in prompts:
            self._append_event(
                session_id=session_id,
                action="prompt",
                actor_type="human",
                actor_id="user",
                content=prompt,
                provenance={"langchain": {"run_id": run_id, "parent_run_id": parent_run_id}},
            )
        if run_id:
            self._chain_sessions.setdefault(run_id, session_id)
        self._append_event(
            session_id=session_id,
            action="system",
            actor_type="system",
            actor_id=actor_id,
            content="LLM execution started",
            provenance={"langchain": {"run_id": run_id, "parent_run_id": parent_run_id}},
        )

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        run_id = kwargs.get("run_id")
        parent_run_id = kwargs.get("parent_run_id")
        session_id = self._resolve_session_id(run_id=run_id, fallback_parent=parent_run_id)

        text_output = _first_generation_text(response)
        metrics = _extract_metrics(response.llm_output if hasattr(response, "llm_output") else None)

        self._append_event(
            session_id=session_id,
            action="completion",
            actor_type="agent",
            actor_id="llm",
            content=text_output,
            metrics=metrics if self.include_metrics else None,
            provenance={"langchain": {"run_id": run_id, "parent_run_id": parent_run_id}},
        )
        if run_id:
            self._chain_sessions.pop(run_id, None)

    # ------------------------------------------------------------------
    # Tool callbacks
    # ------------------------------------------------------------------
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> None:
        run_id = kwargs.get("run_id")
        parent_run_id = kwargs.get("parent_run_id")
        session_id = self._resolve_session_id(run_id=parent_run_id)
        tool_name = serialized.get("name") or "tool"
        if run_id:
            self._tool_names[run_id] = tool_name
        self._append_event(
            session_id=session_id,
            action="tool_call",
            actor_type="tool",
            actor_id=tool_name,
            content=input_str,
            provenance={"langchain": {"run_id": run_id, "parent_run_id": parent_run_id}},
        )

    def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        run_id = kwargs.get("run_id")
        parent_run_id = kwargs.get("parent_run_id")
        session_id = self._resolve_session_id(run_id=parent_run_id)
        tool_name = self._tool_names.pop(run_id, "tool") if run_id else "tool"
        self._append_event(
            session_id=session_id,
            action="tool_result",
            actor_type="tool",
            actor_id=tool_name,
            content=str(output),
            provenance={"langchain": {"run_id": run_id, "parent_run_id": parent_run_id}},
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _resolve_session_id(
        self,
        *,
        run_id: Optional[str] = None,
        fallback_parent: Optional[str] = None,
    ) -> str:
        if run_id and run_id in self._chain_sessions:
            return self._chain_sessions[run_id]
        if fallback_parent and fallback_parent in self._chain_sessions:
            return self._chain_sessions[fallback_parent]
        return self.default_session_id

    def _append_event(
        self,
        *,
        session_id: str,
        action: str,
        actor_type: str,
        actor_id: str,
        content: Optional[str] = None,
        metrics: Optional[_LLMMetrics] = None,
        provenance: Optional[Dict[str, Any]] = None,
    ) -> None:
        event_kwargs: Dict[str, Any] = {
            "session_id": session_id,
            "actor": {"type": actor_type, "id": actor_id},
            "action": action,
        }
        if content is not None:
            event_kwargs["content"] = {"text": content}
        if metrics is not None and any(
            value is not None for value in [metrics.prompt_tokens, metrics.completion_tokens, metrics.total_tokens, metrics.cost_usd]
        ):
            tokens = {}
            if metrics.prompt_tokens is not None:
                tokens["prompt"] = metrics.prompt_tokens
            if metrics.completion_tokens is not None:
                tokens["completion"] = metrics.completion_tokens
            if metrics.total_tokens is not None:
                tokens["total"] = metrics.total_tokens
            event_kwargs["metrics"] = {
                "tokens": tokens or None,
                "cost_usd": metrics.cost_usd,
            }
        if provenance is not None:
            event_kwargs["provenance"] = provenance
        self.session.append(Event(**event_kwargs))


def _first_generation_text(response: Any) -> str:
    generations = getattr(response, "generations", None)
    if not generations:
        return ""
    first = generations[0][0] if isinstance(generations[0], list) else generations[0]
    return getattr(first, "text", str(first))


def _extract_metrics(llm_output: Optional[Dict[str, Any]]) -> Optional[_LLMMetrics]:
    if not llm_output:
        return None
    token_usage = llm_output.get("token_usage") or {}
    prompt_tokens = token_usage.get("prompt_tokens")
    completion_tokens = token_usage.get("completion_tokens")
    total_tokens = token_usage.get("total_tokens")
    cost = _extract_cost(llm_output)
    if cost is None:
        model_name = llm_output.get("model_name") or llm_output.get("model")
        cost = _estimate_cost(model_name, prompt_tokens, completion_tokens)
    return _LLMMetrics(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cost_usd=cost,
    )


_OPENAI_PRICING_USD_PER_TOKEN = {
    "gpt-3.5-turbo": {"prompt": 0.0015 / 1000, "completion": 0.002 / 1000},
    "gpt-3.5-turbo-0613": {"prompt": 0.0015 / 1000, "completion": 0.002 / 1000},
    "gpt-4": {"prompt": 0.03 / 1000, "completion": 0.06 / 1000},
    "gpt-4-0613": {"prompt": 0.03 / 1000, "completion": 0.06 / 1000},
}


def _estimate_cost(
    model_name: Optional[str],
    prompt_tokens: Optional[int],
    completion_tokens: Optional[int],
) -> Optional[float]:
    if not model_name or model_name not in _OPENAI_PRICING_USD_PER_TOKEN:
        return None
    pricing = _OPENAI_PRICING_USD_PER_TOKEN[model_name]
    prompt_cost = (prompt_tokens or 0) * pricing["prompt"]
    completion_cost = (completion_tokens or 0) * pricing["completion"]
    return round(prompt_cost + completion_cost, 6)


def _extract_cost(llm_output: Dict[str, Any]) -> Optional[float]:
    for key in ("cost", "cost_usd", "total_cost", "estimated_cost"):
        value = llm_output.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return None
