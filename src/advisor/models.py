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
    """What we know about a student, for prereq/eligibility reasoning."""

    program: Optional[str] = None
    # completed course code -> grade (e.g. "A", "B+", "T" for transfer/AP)
    completed: dict[str, Optional[str]] = Field(default_factory=dict)
    in_progress: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    notes: Optional[str] = None

    def completed_with_inprogress(self) -> dict[str, Optional[str]]:
        """Completed courses plus in-progress ones (treated as satisfied for
        forward-planning prereq checks)."""
        merged = dict(self.completed)
        for c in self.in_progress:
            merged.setdefault(c, "IP")
        return merged
