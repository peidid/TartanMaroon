"""Normalize the heterogeneous ``data/schedules/`` files into ``Offering`` rows.

Three of the files are flat arrays with *drifting* column names across years
(capacity is variously ``Component - Scheduling enrollment`` / ``Max Enrollment``
/ ``MAX CAPACITY``); one is a nested ``{semester, offerings[{course_code,
sections[]}]}`` object. Calendars and microcourses are handled elsewhere.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ..models import Offering
from .load_courses import normalize_code

# Flat array files -> normalized semester label.
_FLAT_FILES = {
    "Fall_2024_courses.json": "Fall 2024",
    "Spring_2025_courses.json": "Spring 2025",
    "Fall_2025_courses.json": "Fall 2025",
}

# Capacity column has drifted between years; try each.
_CAPACITY_KEYS = ("Max Enrollment", "MAX CAPACITY", "Component - Scheduling enrollment")
_SECTION_KEYS = ("Section", "Section - ID")


def _to_int(v) -> Optional[int]:
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def _first(row: dict, keys) -> Optional[str]:
    for k in keys:
        if row.get(k) not in (None, ""):
            return str(row[k])
    return None


def _load_flat(path: Path, semester: str) -> list[Offering]:
    rows = json.loads(path.read_text())
    out = []
    for r in rows:
        code = normalize_code(r.get("Course - ID", ""))
        if not code:
            continue
        out.append(Offering(
            course_code=code,
            semester=semester,
            section=_first(r, _SECTION_KEYS),
            days=r.get("Delivery times - Day"),
            start_time=r.get("Delivery times - Start time"),
            end_time=r.get("Delivery times - End time"),
            instructor=r.get("Professor - Last name"),
            delivery=r.get("Delivery method"),
            max_enrollment=_to_int(_first(r, _CAPACITY_KEYS)),
        ))
    return out


def _load_nested(path: Path) -> list[Offering]:
    d = json.loads(path.read_text())
    sem = d.get("semester") or {}
    semester = f"{sem.get('term', '')} {sem.get('year', '')}".strip()
    out = []
    for off in d.get("offerings", []):
        code = normalize_code(off.get("course_code", ""))
        for s in off.get("sections", []):
            days = s.get("days")
            out.append(Offering(
                course_code=code,
                semester=semester,
                section=s.get("section"),
                days=" ".join(days) if isinstance(days, list) else days,
                start_time=s.get("start_time"),
                end_time=s.get("end_time"),
                instructor=s.get("instructor"),
                max_enrollment=_to_int(s.get("capacity")),
            ))
    return out


def load_offerings(data_dir: Path) -> list[Offering]:
    sched = Path(data_dir) / "schedules"
    out: list[Offering] = []
    for fname, semester in _FLAT_FILES.items():
        p = sched / fname
        if p.exists():
            out.extend(_load_flat(p, semester))
    nested = sched / "schedule_2026_spring.json"
    if nested.exists():
        out.extend(_load_nested(nested))
    return out
