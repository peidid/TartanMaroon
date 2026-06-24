"""Normalized requirement model shared across all program shapes.

A program's requirements become a recursive :class:`Requirement` tree whose
leaves carry a :class:`CourseSet` (an eligibility predicate: explicit codes,
subject-code prefixes, numeric ranges, plus additions/exclusions). This single
shape is produced from the 5 raw JSON layouts (majors, minors, two gen-ed
variants, concentrations) by ``normalize.py``.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


def split_code(code: str) -> tuple[str, Optional[int]]:
    """``15-451`` -> ``("15", 451)``; ``QC-211`` -> ``("QC", 211)``."""
    code = (code or "").upper().strip()
    if "-" in code:
        dept, num = code.split("-", 1)
        try:
            return dept, int(num)
        except ValueError:
            return dept, None
    return code, None


class CourseSet(BaseModel):
    """A set of eligible courses, defined explicitly and/or by predicate."""

    explicit: list[str] = Field(default_factory=list)
    subject_codes: list[str] = Field(default_factory=list)
    ranges: list[tuple[str, int, int]] = Field(default_factory=list)        # (dept, lo, hi)
    additional: list[str] = Field(default_factory=list)
    excluded: list[str] = Field(default_factory=list)
    excluded_ranges: list[tuple[str, int, int]] = Field(default_factory=list)

    def matches(self, code: str) -> bool:
        code = code.upper()
        dept, num = split_code(code)
        if code in {c.upper() for c in self.excluded}:
            return False
        if num is not None and any(dept == d and lo <= num <= hi for d, lo, hi in self.excluded_ranges):
            return False
        if code in {c.upper() for c in self.explicit} or code in {c.upper() for c in self.additional}:
            return True
        if dept in self.subject_codes:
            return True
        if num is not None and any(dept == d and lo <= num <= hi for d, lo, hi in self.ranges):
            return True
        return False

    def is_predicate(self) -> bool:
        """True if it relies on subject codes / ranges (needs the catalog to enumerate)."""
        return bool(self.subject_codes or self.ranges)

    def resolve(self, all_codes: list[str]) -> list[str]:
        if self.is_predicate():
            return sorted(c for c in all_codes if self.matches(c))
        out = {c.upper() for c in self.explicit} | {c.upper() for c in self.additional}
        out -= {c.upper() for c in self.excluded}
        return sorted(out)

    def describe(self) -> str:
        parts = []
        if self.explicit:
            shown = self.explicit[:8]
            parts.append("{" + ", ".join(shown) + ("…" if len(self.explicit) > 8 else "") + "}")
        if self.subject_codes:
            parts.append("subject " + "/".join(self.subject_codes))
        if self.ranges:
            parts.append(", ".join(f"{d}-{lo:03d}…{d}-{hi:03d}" for d, lo, hi in self.ranges))
        if self.additional:
            parts.append(f"+{len(self.additional)} more")
        if self.excluded or self.excluded_ranges:
            parts.append(f"−{len(self.excluded) + len(self.excluded_ranges)} excluded")
        return "; ".join(parts) or "(unspecified)"


RequirementKind = Literal["all", "choose", "units", "course", "note"]


class Requirement(BaseModel):
    name: str
    kind: RequirementKind
    n: Optional[int] = None                     # choose: number of courses
    min_units: Optional[float] = None           # units: target units
    course_set: Optional[CourseSet] = None
    min_grade: Optional[str] = None
    children: list["Requirement"] = Field(default_factory=list)
    note: Optional[str] = None
    constraints: list[str] = Field(default_factory=list)

    def leaves(self) -> list["Requirement"]:
        if self.kind in ("course", "choose", "units", "note"):
            return [self]
        out: list[Requirement] = []
        for c in self.children:
            out.extend(c.leaves())
        return out


class Program(BaseModel):
    key: str
    name: str
    kind: Literal["major", "minor", "gened", "concentration"]
    total_units: Optional[float] = None
    double_counting_rules: dict = Field(default_factory=dict)
    root: Requirement


# ---- progress reporting ----

class RequirementProgress(BaseModel):
    name: str
    kind: str
    satisfied: bool
    needed: str
    applied_courses: list[str] = Field(default_factory=list)
    remaining: Optional[str] = None
    eligible_examples: list[str] = Field(default_factory=list)
    children: list["RequirementProgress"] = Field(default_factory=list)


class ProgressReport(BaseModel):
    program: str
    overall_satisfied: bool
    summary: str
    requirements: list[RequirementProgress]
    unmet: list[str]
    caveat: str


Requirement.model_rebuild()
RequirementProgress.model_rebuild()
