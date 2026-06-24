"""Typed domain models for the advising backbone.

These wrap the raw ``data/`` JSON in validated, queryable shapes. ``Course`` is
the workhorse — it carries the parsed prereq AST so tools can reason about
prerequisites without re-parsing.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from .prereqs.ast import PrereqExpr


class CourseRef(BaseModel):
    """A lightweight reference to another course (co-req / anti-req / equiv)."""

    code: str
    name: Optional[str] = None
    units: Optional[float] = None


class Course(BaseModel):
    code: str
    name: str
    short_name: Optional[str] = None
    units: Optional[float] = None
    min_units: Optional[float] = None
    max_units: Optional[float] = None

    prereqs_text: Optional[str] = None
    prereq_ast: Optional[PrereqExpr] = None

    co_reqs: list[CourseRef] = Field(default_factory=list)
    anti_reqs: list[CourseRef] = Field(default_factory=list)
    equiv: list[CourseRef] = Field(default_factory=list)

    long_desc: Optional[str] = None
    website: Optional[str] = None
    custom_fields: dict = Field(default_factory=dict)

    @property
    def dept(self) -> str:
        """Department code prefix, e.g. ``15`` for ``15-122`` (``QC`` for ``QC-211``)."""
        return self.code.split("-", 1)[0]

    def direct_prereq_courses(self) -> set[str]:
        return self.prereq_ast.referenced_courses() if self.prereq_ast else set()


class Offering(BaseModel):
    """One scheduled section of a course in a given semester."""

    course_code: str
    semester: str                  # normalized, e.g. "Fall 2025"
    section: Optional[str] = None
    days: Optional[str] = None     # e.g. "Tuesday Thursday Sunday"
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    instructor: Optional[str] = None
    delivery: Optional[str] = None
    max_enrollment: Optional[int] = None


class StudentState(BaseModel):
    """What we know about a student, for prereq/eligibility reasoning and
    for personalizing the advisor's answers."""

    name: Optional[str] = None
    program: Optional[str] = None          # primary major (free text; fuzzy-matched)
    year: Optional[str] = None             # e.g. "Sophomore"
    gpa: Optional[float] = None
    minors: list[str] = Field(default_factory=list)
    concentration: Optional[str] = None
    expected_graduation: Optional[str] = None

    # completed course code -> grade (e.g. "A", "B+", "T" for transfer/AP)
    completed: dict[str, Optional[str]] = Field(default_factory=dict)
    in_progress: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    career_goals: list[str] = Field(default_factory=list)
    notes: Optional[str] = None

    def completed_with_inprogress(self) -> dict[str, Optional[str]]:
        """Completed courses plus in-progress ones (treated as satisfied for
        forward-planning prereq checks)."""
        merged = dict(self.completed)
        for c in self.in_progress:
            merged.setdefault(c, "IP")
        return merged

    def has_profile(self) -> bool:
        """True if the student has entered anything worth personalizing on."""
        return bool(
            self.name or self.program or self.year or self.completed
            or self.in_progress or self.interests or self.career_goals
            or self.minors or self.concentration
        )

    def to_dict(self) -> dict:
        """Plain, JSON-serializable view of the profile (for the my_profile tool)."""
        return {
            "name": self.name,
            "program": self.program,
            "year": self.year,
            "gpa": self.gpa,
            "minors": self.minors,
            "concentration": self.concentration,
            "expected_graduation": self.expected_graduation,
            "completed_courses": self.completed,
            "in_progress": self.in_progress,
            "interests": self.interests,
            "career_goals": self.career_goals,
        }

    def profile_summary(self) -> str:
        """A compact, human-readable profile block to inject into the system
        prompt so the orchestrator always knows who it is advising."""
        if not self.has_profile():
            return (
                "STUDENT PROFILE: none on file yet. Don't assume a major, year, or "
                "completed courses — ask the student for the details you need, and "
                "suggest they fill in their profile for personalized advice."
            )
        lines: list[str] = ["STUDENT PROFILE (the student you are advising):"]
        if self.name:
            lines.append(f"- Name: {self.name}")
        if self.program:
            lines.append(f"- Major: {self.program}")
        if self.year:
            lines.append(f"- Year: {self.year}")
        if self.expected_graduation:
            lines.append(f"- Expected graduation: {self.expected_graduation}")
        if self.minors:
            lines.append(f"- Minor(s): {', '.join(self.minors)}")
        if self.concentration:
            lines.append(f"- Concentration: {self.concentration}")
        if self.gpa is not None:
            lines.append(f"- GPA: {self.gpa}")
        if self.interests:
            lines.append(f"- Interests: {', '.join(self.interests)}")
        if self.career_goals:
            lines.append(f"- Career goals: {', '.join(self.career_goals)}")
        if self.completed:
            done = ", ".join(
                f"{code} ({grade})" if grade else code
                for code, grade in sorted(self.completed.items())
            )
            lines.append(f"- Completed courses: {done}")
        if self.in_progress:
            lines.append(f"- In progress: {', '.join(self.in_progress)}")
        lines.append(
            "Use this profile to personalize advice. The eligibility and "
            "degree-progress tools already apply these completed courses "
            "automatically — you don't need to ask the student to re-list them."
        )
        return "\n".join(lines)
