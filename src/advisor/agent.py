"""Pydantic AI orchestrator: an LLM that plans and calls the advising tools.

The orchestrator never asserts course facts on its own — every prerequisite,
eligibility, or offering claim must come from a tool call over the verified
structured backbone. This is the engineering analogue of the research program's
"verify, don't hope" principle.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic_ai import Agent, RunContext

from .config import settings
from .models import StudentState
from .repository.base import Repository
from .retrieval import library
from .tools import advising


@dataclass
class Deps:
    repo: Repository
    student: StudentState


SYSTEM_PROMPT = """\
You are an academic advising assistant for Carnegie Mellon University in Qatar
(CMU-Q). You help students understand courses, prerequisites, eligibility, and
course offerings.

Rules:
- NEVER state a prerequisite, eligibility verdict, course code, or offering from
  memory. Always call a tool and base your answer on its result.
- When the question is about whether the student can take a course, use
  `check_eligibility` (the student's completed courses are already known to the
  tools — you do not need to ask for them unless they want a hypothetical).
- Plan multi-step questions: call several tools, then synthesize one clear answer.
- Cite course codes (e.g. 15-122) and be concise. If a tool returns an error or
  no data, say so plainly rather than guessing.
- For "what's left for my degree / can I add this minor" questions about a
  student's GRADUATION progress in a program, use `degree_progress`. Pass along
  its `unmet_requirements` and surface the `double_counting_rules` and `caveat`
  honestly — progress is an estimate, not a registrar audit.
- IMPORTANT — distinguish two different questions:
  • "What do I need to TRANSFER INTO / CHANGE MY MAJOR TO X?" = an ADMISSION
    POLICY question. Answer it from the "Policy on Changing Majors" document via
    `find_documents` + `read_document`. Do NOT answer it with `degree_progress`
    (that returns graduation requirements, which is a different thing).
  • "What's left to GRADUATE in X?" = `degree_progress`.
- For policy / advising / handbook questions (changing majors, grade appeals,
  overload approval, academic integrity, financial aid, etc.), use the document
  tools: `find_documents` to locate the right document, then `read_document` to
  read it IN FULL and quote the exact text. Use `list_documents` to browse the
  catalog if a search is unclear. The full handbook is available to you — NEVER
  ask the student to paste or point you to a policy/document; find and read it
  yourself. If one search misses, try different wording before giving up.
- A STUDENT PROFILE is given to you below (major, year, completed courses,
  interests, etc.). Use it to personalize answers — when a student asks "what
  should I take?" or "what's left for my degree?", reason from their profile and
  the tools. Their completed courses are already wired into the eligibility and
  degree-progress tools. Call `my_profile` if you need the raw profile values
  (e.g. to quote their GPA or interests).
"""


def build_agent() -> Agent[Deps, str]:
    agent: Agent[Deps, str] = Agent(
        f"openai:{settings.chat_model}",
        deps_type=Deps,
        system_prompt=SYSTEM_PROMPT,
    )

    @agent.system_prompt
    def student_profile_prompt(ctx: RunContext[Deps]) -> str:
        """Inject the current student's profile so the orchestrator always knows
        who it is advising (appended to the static system prompt each run)."""
        return ctx.deps.student.profile_summary()

    @agent.tool
    def my_profile(ctx: RunContext[Deps]) -> dict:
        """Return the current student's stored profile (major, year, completed
        courses with grades, interests, goals, GPA)."""
        return ctx.deps.student.to_dict()

    @agent.tool
    def find_courses(ctx: RunContext[Deps], query: str, limit: int = 10) -> list[dict]:
        """Search the catalog by code, title, or keyword."""
        return advising.find_courses(ctx.deps.repo, query, limit)

    @agent.tool
    def course_details(ctx: RunContext[Deps], code: str) -> dict:
        """Get full details for one course (units, prereqs, description, etc.)."""
        return advising.course_details(ctx.deps.repo, code)

    @agent.tool
    def prerequisites(ctx: RunContext[Deps], code: str) -> dict:
        """Get the direct and full transitive prerequisites of a course."""
        return advising.prerequisites(ctx.deps.repo, code)

    @agent.tool
    def check_eligibility(ctx: RunContext[Deps], course: str) -> dict:
        """Check whether the current student is eligible to take a course."""
        return advising.check_eligibility(
            ctx.deps.repo, course, ctx.deps.student.completed_with_inprogress()
        )

    @agent.tool
    def courses_unlocked_by(ctx: RunContext[Deps], code: str) -> dict:
        """List what a course is a prerequisite for (directly and transitively)."""
        return advising.courses_unlocked_by(ctx.deps.repo, code)

    @agent.tool
    def course_offerings(ctx: RunContext[Deps], code: str) -> list[dict]:
        """List all known scheduled sections of a course across semesters."""
        return advising.course_offerings(ctx.deps.repo, code)

    @agent.tool
    def is_offered(ctx: RunContext[Deps], code: str, semester: str) -> dict:
        """Check if a course is offered in a semester, e.g. 'Spring 2026'."""
        return advising.is_offered(ctx.deps.repo, code, semester)

    @agent.tool
    def list_semesters(ctx: RunContext[Deps]) -> list[str]:
        """List semesters for which schedule data is available."""
        return advising.list_semesters(ctx.deps.repo)

    @agent.tool
    def list_programs(ctx: RunContext[Deps]) -> list[dict]:
        """List all majors and minors and their lookup keys."""
        return advising.list_programs(ctx.deps.repo)

    @agent.tool
    def program_requirements(ctx: RunContext[Deps], program: str) -> dict:
        """Get the requirement structure of a program (major or minor)."""
        return advising.program_requirements(ctx.deps.repo, program)

    @agent.tool
    def degree_progress(ctx: RunContext[Deps], program: str = "") -> dict:
        """What the current student still needs for a program (defaults to their own)."""
        prog = program or ctx.deps.student.program or ""
        return advising.degree_progress(
            ctx.deps.repo, prog, ctx.deps.student.completed_with_inprogress()
        )

    @agent.tool
    def find_documents(ctx: RunContext[Deps], query: str, k: int = 5) -> list[dict]:
        """Find handbook/policy/advising documents by keyword. Returns ranked
        matches with a context snippet and the document's section outline. Follow
        up with `read_document(source)` to read the full text."""
        return library.find_documents(query, k)

    @agent.tool
    def read_document(ctx: RunContext[Deps], source: str, offset: int = 0) -> dict:
        """Read a full handbook/policy/advising document by its `source` path
        (from find_documents/list_documents). Returns the complete cleaned text;
        if `truncated`, call again with the returned `next_offset`."""
        return library.read_document(source, offset)

    @agent.tool
    def list_documents(ctx: RunContext[Deps], category: str = "") -> list[dict]:
        """Browse the handbook/policy/advising catalog (title + summary per doc).
        Optionally filter by category, e.g. 'policies', 'programs', 'student_life'."""
        return library.list_documents(category)

    return agent
