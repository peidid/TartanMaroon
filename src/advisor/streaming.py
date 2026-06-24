"""Normalized streaming events for the advising agent.

Wraps Pydantic AI's ``agent.iter()`` graph traversal into a single async stream
of small, serializable :class:`AdvisorEvent` objects: the model's thinking and
answer tokens, every tool call (with args), and every tool result. The CLI
renders these; a web backend can serialize the same events to SSE for the
Vercel UI — one source of truth for "show the working process".
"""

from __future__ import annotations

import json
from typing import AsyncIterator, Literal, Optional

from pydantic import BaseModel
from pydantic_ai import Agent
import pydantic_ai.messages as msg


class AdvisorEvent(BaseModel):
    type: Literal["thinking", "text", "tool_call", "tool_result", "done", "error"]
    text: Optional[str] = None
    tool: Optional[str] = None
    args: Optional[dict] = None
    result: Optional[str] = None


def _args_to_dict(part) -> dict:
    try:
        return part.args_as_dict()
    except Exception:
        a = getattr(part, "args", None)
        if isinstance(a, dict):
            return a
        if isinstance(a, str):
            try:
                return json.loads(a)
            except json.JSONDecodeError:
                return {"raw": a}
        return {}


def _summarize_result(result) -> str:
    content = getattr(result, "content", result)
    s = content if isinstance(content, str) else json.dumps(content, default=str)
    return s[:240] + ("…" if len(s) > 240 else "")


class AgentStreamer:
    """Drives one agent run, yielding normalized events; keeps message history."""

    def __init__(self, agent: Agent, deps):
        self.agent = agent
        self.deps = deps
        self.last_messages = None

    async def stream(self, prompt: str, history=None) -> AsyncIterator[AdvisorEvent]:
        try:
            async with self.agent.iter(prompt, deps=self.deps, message_history=history) as run:
                async for node in run:
                    if Agent.is_model_request_node(node):
                        async with node.stream(run.ctx) as s:
                            async for ev in s:
                                out = self._model_event(ev)
                                if out:
                                    yield out
                    elif Agent.is_call_tools_node(node):
                        async with node.stream(run.ctx) as s:
                            async for ev in s:
                                out = self._tool_event(ev)
                                if out:
                                    yield out
                self.last_messages = run.result.all_messages()
                yield AdvisorEvent(type="done", text=run.result.output)
        except Exception as e:  # surface failures as a stream event, don't crash the UI
            yield AdvisorEvent(type="error", text=f"{type(e).__name__}: {e}")

    @staticmethod
    def _model_event(ev) -> Optional[AdvisorEvent]:
        if isinstance(ev, msg.PartStartEvent):
            part = ev.part
            if isinstance(part, msg.TextPart) and part.content:
                return AdvisorEvent(type="text", text=part.content)
            if isinstance(part, msg.ThinkingPart) and part.content:
                return AdvisorEvent(type="thinking", text=part.content)
        elif isinstance(ev, msg.PartDeltaEvent):
            d = ev.delta
            if isinstance(d, msg.TextPartDelta) and d.content_delta:
                return AdvisorEvent(type="text", text=d.content_delta)
            if isinstance(d, msg.ThinkingPartDelta) and getattr(d, "content_delta", None):
                return AdvisorEvent(type="thinking", text=d.content_delta)
        return None

    @staticmethod
    def _tool_event(ev) -> Optional[AdvisorEvent]:
        if isinstance(ev, msg.FunctionToolCallEvent):
            return AdvisorEvent(type="tool_call", tool=ev.part.tool_name, args=_args_to_dict(ev.part))
        if isinstance(ev, msg.FunctionToolResultEvent):
            return AdvisorEvent(type="tool_result",
                                tool=getattr(ev.part, "tool_name", None),
                                result=_summarize_result(ev.part))
        return None
