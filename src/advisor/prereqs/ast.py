"""Typed AST for parsed prerequisite expressions.

Prereq text in the catalog is a boolean expression over atoms of the form
``COURSE [] at least GRADE`` combined with ``and`` / ``or`` and parentheses
(e.g. ``"((15-122 [] at least C) or (15-121 [] at least C)) and ..."``).

These nodes are Pydantic models so they serialize cleanly into storage and as
tool return values. A parsed expression answers two questions the advising
tools need: which courses it references, and whether a student's completed
coursework satisfies it.
"""

from __future__ import annotations

from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field

# Worst -> best. Ranks let "at least C" mean rank(grade) >= rank("C").
_GRADE_ORDER = [
    "F", "R", "W", "D-", "D", "D+",
    "C-", "C", "C+", "B-", "B", "B+", "A-", "A", "A+",
]
_GRADE_RANK = {g: i for i, g in enumerate(_GRADE_ORDER)}

# Non-letter marks that count as "completed and passing" for prereq purposes
# (pass / satisfactory / transfer / advanced placement / in-progress for
# forward planning). Refined later against real records.
_PASSING_NONLETTER = {"P", "S", "T", "AP", "IP"}


def grade_meets(student_grade: Optional[str], min_grade: Optional[str]) -> bool:
    """True if ``student_grade`` satisfies a ``min_grade`` threshold."""
    if not min_grade:
        return True
    if not student_grade:
        return False
    g = student_grade.strip().upper()
    if g in _PASSING_NONLETTER:
        return True
    return _GRADE_RANK.get(g, -1) >= _GRADE_RANK.get(min_grade.strip().upper(), 99)


class Atom(BaseModel):
    """A single course requirement, optionally with a minimum grade."""

    kind: Literal["atom"] = "atom"
    course: str
    min_grade: Optional[str] = None

    def referenced_courses(self) -> set[str]:
        return {self.course}

    def satisfied_by(self, completed: dict[str, Optional[str]]) -> bool:
        if self.course not in completed:
            return False
        return grade_meets(completed[self.course], self.min_grade)

    def describe(self) -> str:
        return self.course + (f" (≥{self.min_grade})" if self.min_grade else "")


class And(BaseModel):
    kind: Literal["and"] = "and"
    children: list["PrereqExpr"]

    def referenced_courses(self) -> set[str]:
        out: set[str] = set()
        for c in self.children:
            out |= c.referenced_courses()
        return out

    def satisfied_by(self, completed: dict[str, Optional[str]]) -> bool:
        return all(c.satisfied_by(completed) for c in self.children)

    def describe(self) -> str:
        return "(" + " AND ".join(c.describe() for c in self.children) + ")"


class Or(BaseModel):
    kind: Literal["or"] = "or"
    children: list["PrereqExpr"]

    def referenced_courses(self) -> set[str]:
        out: set[str] = set()
        for c in self.children:
            out |= c.referenced_courses()
        return out

    def satisfied_by(self, completed: dict[str, Optional[str]]) -> bool:
        return any(c.satisfied_by(completed) for c in self.children)

    def describe(self) -> str:
        return "(" + " OR ".join(c.describe() for c in self.children) + ")"


PrereqExpr = Annotated[Union[Atom, And, Or], Field(discriminator="kind")]

And.model_rebuild()
Or.model_rebuild()
