"""Fast greeting / introduction short-circuit.

The full orchestrator (gpt-5.2 + 12 verified tools) is overkill for "hi" or
"what can you do?". Mirroring the old multi-agent system's coordinator triage,
this module uses a small, fast model (``ADVISOR_TRIAGE_MODEL``, default
``gpt-4o-mini``) to classify a message and, for greetings / general questions,
write a short reply directly — so those answer in one cheap call instead of a
full tool-planning loop.

It is deliberately conservative: anything that *might* need advising data is
classified ``academic`` and handed back to the full orchestrator.
"""

from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel
from pydantic_ai import Agent

from .config import settings

# Quick local pre-filter: if a message clearly needs advising data, skip the
# triage LLM entirely and go straight to the orchestrator (saves a round-trip
# on real questions). Greetings/intros are short and hit none of these.
_ACADEMIC_HINT = re.compile(
    r"\b\d{2}-\d{3}\b"  # a course code like 15-122
    r"|prereq|eligib|require|offer|schedul|semester|minor|major|graduat|degree"
    r"|course|credit|\bunit|gpa|polic|grade|regist|overload|elective|concentrat"
    r"|transfer|waitlist|enroll|professor|instructor|exam|deadline",
    re.IGNORECASE,
)


def likely_academic(message: str) -> bool:
    """Cheap heuristic: should we bypass triage and use the full orchestrator?"""
    return len(message) > 120 or bool(_ACADEMIC_HINT.search(message))


class TriageResult(BaseModel):
    category: Literal["greeting", "general", "academic"]
    reply: Optional[str] = None


_TRIAGE_PROMPT = """\
You triage the first line of a student's message for a CMU-Q academic advising \
assistant. Classify into exactly one category:

- "greeting": greetings, smalltalk, thanks, goodbyes (e.g. "hi", "hello there", \
"thanks!", "good morning", "bye").
- "general": questions about the assistant itself or how to use it (e.g. "who \
are you?", "what can you do?", "how does this work?") — NOT about any specific \
course, program, requirement, schedule, or policy.
- "academic": anything that needs real advising data — courses, prerequisites, \
eligibility, schedules, requirements, degree progress, planning, or policies. \
WHEN IN DOUBT, choose "academic".

For "greeting" or "general", write a short, warm `reply` (1-3 sentences) as the \
advisor. Briefly note you can help with courses, prerequisites, schedules, \
degree requirements, and policies. For "academic", leave `reply` empty/null.
"""

_agent: Optional[Agent[None, TriageResult]] = None


def _get_agent() -> Agent[None, TriageResult]:
    global _agent
    if _agent is None:
        _agent = Agent(
            f"openai:{settings.triage_model}",
            output_type=TriageResult,
            system_prompt=_TRIAGE_PROMPT,
        )
    return _agent


async def triage_message(message: str) -> TriageResult:
    """Classify a message. Returns category ``academic`` (and no reply) for
    anything that should go to the full orchestrator — including on any error,
    so triage can never block a real question."""
    if not settings.advisor_triage_enabled:
        return TriageResult(category="academic")
    if likely_academic(message):
        return TriageResult(category="academic")
    try:
        result = await _get_agent().run(message)
        return result.output
    except Exception:
        # Never let triage failure swallow a question — fall through to the agent.
        return TriageResult(category="academic")
