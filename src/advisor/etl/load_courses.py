"""Load raw ``data/courses/*.json`` into validated :class:`Course` models."""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..models import Course, CourseRef
from ..prereqs.parser import parse_prereqs

_FIVE_DIGITS = re.compile(r"^\d{5}$")


def normalize_code(raw: str) -> str:
    """``03121`` -> ``03-121``; already-dashed codes pass through."""
    raw = (raw or "").strip()
    if _FIVE_DIGITS.match(raw):
        return f"{raw[:2]}-{raw[2:]}"
    return raw


def _refs(items) -> list[CourseRef]:
    out = []
    for it in items or []:
        if isinstance(it, dict) and it.get("code"):
            out.append(CourseRef(code=it["code"], name=it.get("name"), units=it.get("units")))
    return out


def load_courses(data_dir: Path) -> dict[str, Course]:
    courses: dict[str, Course] = {}
    course_dir = Path(data_dir) / "courses"
    for p in sorted(course_dir.glob("*.json")):
        d = json.loads(p.read_text())
        text = (d.get("prereqs") or {}).get("text") or None
        course = Course(
            code=d["code"],
            name=d.get("name") or d["code"],
            short_name=d.get("short_name"),
            units=d.get("units"),
            min_units=d.get("min_units"),
            max_units=d.get("max_units"),
            prereqs_text=text,
            prereq_ast=parse_prereqs(text),
            co_reqs=_refs(d.get("co_reqs")),
            anti_reqs=_refs(d.get("anti_reqs")),
            equiv=_refs(d.get("equiv")),
            long_desc=d.get("long_desc"),
            website=d.get("website"),
            custom_fields=d.get("custom_fields") or {},
        )
        courses[course.code] = course
    return courses
