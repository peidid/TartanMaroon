"""Normalize the 5 raw program-JSON shapes into the :class:`Requirement` tree.

Strategy: a recursive walker. A node is a GROUP if it has nested requirement
dicts (or ``categories`` / ``option_N`` keys); otherwise it is a selection LEAF
recognised from keys like ``code`` / ``choose_one_from`` / ``courses_required``
/ ``course_range`` / ``subject_codes`` / ``courses``+``min_units``. Mixed nodes
(leaf-keys *and* nested children) are treated as groups whose ``core_courses`` /
``required_courses`` become one child. Anything unrecognised becomes a ``note``
leaf so nothing is silently dropped.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from ..etl.load_courses import normalize_code
from .models import CourseSet, Program, Requirement, split_code

# Keys that are metadata or selection-support (never a nested sub-requirement).
_META = {
    "mode_average_units", "title", "description", "Description", "last_published",
    "published_by", "visibility", "audit_version", "entry_year", "campus",
    "applies_to_students", "note", "notes", "status", "attempts_allowed",
    "minimum_units_per_course", "min_units_per_course", "double_count_restriction",
    "name", "school", "university", "degree", "requirement", "total_units",
    "total_min_units", "total_units_required", "contacts", "contact", "career_paths",
    "pathways", "available", "double_counting_allowed", "restrictions",
}
_SELECTION = {
    "choose_one_from", "courses_required", "course_range", "code", "choose_from",
    "courses", "options", "specific_courses", "subject_codes", "subject_code",
    "additional_courses", "excluded_courses", "excluded_ranges", "minimum_grade",
    "at_least_one_from", "required_course", "min_units", "required_courses",
    "core_courses", "or_biology_course",
}
_NUMWORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7}
_OPTION_RE = re.compile(r"option[_ ]?\d+$", re.IGNORECASE)
_CODE_RE = re.compile(r"^[A-Za-z0-9]{2}-\d{3}$")


def _norm(code: str) -> str:
    return normalize_code(code).upper()


def _code(item) -> Optional[str]:
    if isinstance(item, dict):
        return item.get("code")
    if isinstance(item, str) and _CODE_RE.match(item.strip()):
        return item.strip()
    return None


def _course_name(item) -> str:
    if isinstance(item, dict):
        return item.get("title") or item.get("code") or "course"
    return str(item)


def _courses_from(items) -> list[str]:
    out = []
    for it in items or []:
        c = _code(it)
        if c:
            out.append(_norm(c))
    return out


def _to_int(v) -> Optional[int]:
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def _to_float(v) -> Optional[float]:
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def _humanize(key: str) -> str:
    return key.replace("_", " ").strip().title()


def _at_least_n(text: str) -> Optional[int]:
    text = (text or "").lower()
    m = re.search(r"(?:at least|take)\s+(\d+|one|two|three|four|five|six|seven)", text)
    if m:
        g = m.group(1)
        return int(g) if g.isdigit() else _NUMWORDS.get(g)
    return None


def _parse_range(s) -> Optional[tuple[str, int, int]]:
    """Parse a range from a string ('02-100 to 02-199') or dict ({start, end})."""
    if isinstance(s, dict):
        sd, sn = split_code(s.get("start", ""))
        _, en = split_code(s.get("end", ""))
        return (sd, sn, en) if sn is not None and en is not None else None
    if isinstance(s, str):
        m = re.match(r"\s*([A-Za-z0-9]{2})-(\d{3})\s*(?:to|–|-)\s*([A-Za-z0-9]{2})-(\d{3})", s)
        if m:
            return (m.group(1).upper(), int(m.group(2)), int(m.group(4)))
    return None


def _build_course_set(d: dict, explicit: Optional[list[str]]) -> CourseSet:
    cs = CourseSet(explicit=list(explicit or []))
    for key in ("subject_codes", "subject_code"):
        if key in d:
            v = d[key]
            cs.subject_codes += [str(v)] if isinstance(v, str) else [str(x) for x in v]
    if "additional_courses" in d:
        cs.additional += _courses_from_or_str(d["additional_courses"])
    if "excluded_courses" in d:
        cs.excluded += _courses_from_or_str(d["excluded_courses"])
    for s in d.get("excluded_ranges", []) or []:
        r = _parse_range(s)
        if r:
            cs.excluded_ranges.append(r)
    if "course_range" in d and isinstance(d["course_range"], dict):
        cr = d["course_range"]
        sd, sn = split_code(cr.get("start", ""))
        _, en = split_code(cr.get("end", ""))
        if sn is not None and en is not None:
            cs.ranges.append((sd, sn, en))
    return cs


def _courses_from_or_str(items) -> list[str]:
    """additional/excluded lists are often bare strings ('02-223')."""
    out = []
    for it in items or []:
        if isinstance(it, str) and _CODE_RE.match(it.strip()):
            out.append(_norm(it))
        else:
            c = _code(it)
            if c:
                out.append(_norm(c))
    return out


def _foreign_children(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        if k in _META or k in _SELECTION or _OPTION_RE.match(k):
            continue
        if isinstance(v, dict):
            out[k] = v
    return out


def _course_leaf(item, name: Optional[str] = None) -> Optional[Requirement]:
    c = _code(item)
    if not c:
        return None
    return Requirement(name=name or _course_name(item), kind="course",
                       course_set=CourseSet(explicit=[_norm(c)]))


def normalize_node(name: str, d) -> Optional[Requirement]:
    if not isinstance(d, dict):
        return None
    req_str = str(d.get("requirement", "")).lower()
    group_kind = "choose" if "any of" in req_str else "all"
    group_n = 1 if group_kind == "choose" else None

    # OR over option_N keys.
    option_keys = sorted(k for k in d if _OPTION_RE.match(k))
    if option_keys:
        kids = [normalize_node(_humanize(k), d[k]) for k in option_keys]
        kids = [k for k in kids if k]
        return Requirement(name=name, kind="choose", n=1, children=kids,
                           constraints=[d["requirement"]] if d.get("requirement") else [])

    # Explicit category container.
    if isinstance(d.get("categories"), dict):
        kids = [normalize_node(_humanize(k), v) for k, v in d["categories"].items() if isinstance(v, dict)]
        kids = [k for k in kids if k]
        return Requirement(name=name, kind=group_kind, n=group_n, children=kids)

    foreign = _foreign_children(d)
    if foreign:
        kids: list[Requirement] = []
        for key, label in (("core_courses", "Core Courses"), ("required_courses", "Required Courses")):
            if isinstance(d.get(key), list):
                courses = [c for c in (_course_leaf(it) for it in d[key]) if c]
                if courses:
                    kids.append(Requirement(name=label, kind="all", children=courses))
        for k, v in foreign.items():
            child = normalize_node(_humanize(k), v)
            if child:
                kids.append(child)
        return Requirement(name=name, kind=group_kind, n=group_n, children=kids)

    # ---- selection leaves (no nested children) ----
    if isinstance(d.get("code"), str):
        return Requirement(name=name, kind="course",
                           course_set=CourseSet(explicit=[_norm(d["code"])]),
                           min_grade=d.get("minimum_grade"))
    if isinstance(d.get("required_course"), dict) and d["required_course"].get("code"):
        return Requirement(name=name, kind="course",
                           course_set=CourseSet(explicit=[_norm(d["required_course"]["code"])]))
    if "choose_one_from" in d:
        return Requirement(name=name, kind="choose", n=1,
                           course_set=CourseSet(explicit=_courses_from(d["choose_one_from"])),
                           min_grade=d.get("minimum_grade"))
    for key, label in (("required_courses", "all required"), ("core_courses", "all core")):
        if isinstance(d.get(key), list):
            courses = [c for c in (_course_leaf(it) for it in d[key]) if c]
            return Requirement(name=name, kind="all", children=courses)

    n = _to_int(d.get("courses_required")) if "courses_required" in d else None
    if n is None:
        n = _at_least_n(req_str)
    explicit = None
    for key in ("choose_from", "specific_courses", "courses", "options"):
        if isinstance(d.get(key), list):
            cf = _courses_from(d[key])
            if cf:
                explicit = cf
                break
    if n is not None or "course_range" in d or "subject_codes" in d or "subject_code" in d:
        cs = _build_course_set(d, explicit)
        constraints = []
        if "at_least_one_from" in d:
            atl = _courses_from(d["at_least_one_from"])
            for c in atl:
                if c not in cs.explicit:
                    cs.explicit.append(c)
            if atl:
                constraints.append("at least one of " + ", ".join(atl))
        return Requirement(name=name, kind="choose", n=n or 1, course_set=cs,
                           min_grade=d.get("minimum_grade"), constraints=constraints)

    if isinstance(d.get("courses"), list):
        cs = CourseSet(explicit=_courses_from(d["courses"]))
        mu = _to_float(d.get("min_units"))
        if mu:
            return Requirement(name=name, kind="units", min_units=mu, course_set=cs)
        return Requirement(name=name, kind="choose", n=1, course_set=cs)

    raw = d.get("requirement") or d.get("description") or ""
    return Requirement(name=name, kind="note", note=(str(raw)[:200] or "(unstructured requirement)"))


def _gened_root(raw: dict) -> Optional[dict]:
    for path in [
        ("general_requirement", "general_rules", "requirements"),
        ("program", "general_requirements", "general_education"),
        ("general_requirements", "general_education"),
        ("general_education",),
        ("general_requirement",),
    ]:
        node = raw
        ok = True
        for p in path:
            if isinstance(node, dict) and p in node:
                node = node[p]
            else:
                ok = False
                break
        if ok and isinstance(node, dict):
            return node
    return None


def normalize_major(raw: dict, key: str) -> Program:
    prog = raw.get("program", {})
    pr = raw.get("program_requirements", {})
    root = normalize_node("Degree Requirements", raw.get("requirements", {}))
    return Program(
        key=key, name=prog.get("title", key), kind="major",
        total_units=_to_float(pr.get("total_units_required")),
        double_counting_rules=pr.get("double_counting_rules", {}) or {},
        root=root or Requirement(name="Degree Requirements", kind="all"),
    )


def normalize_minor(raw: dict, key: str) -> Program:
    minor = raw.get("minor", {})
    pr = raw.get("program_requirements", {})
    root = normalize_node("Minor Requirements", pr.get("requirements", {}))
    return Program(
        key=key, name=minor.get("name", key), kind="minor",
        total_units=_to_float(pr.get("total_min_units") or pr.get("total_units")),
        double_counting_rules=pr.get("double_counting_rules", {}) or {},
        root=root or Requirement(name="Minor Requirements", kind="all"),
    )


def normalize_gened(raw: dict) -> Optional[Requirement]:
    root_dict = _gened_root(raw)
    if not root_dict:
        return None
    return normalize_node("General Education", root_dict)


def load_programs(data_dir: str | Path) -> dict[str, Program]:
    """Discover and normalize all majors (with gen-ed merged in) and minors."""
    base = Path(data_dir) / "programs"
    programs: dict[str, Program] = {}

    for sub in sorted(base.iterdir()):
        if not sub.is_dir() or sub.name == "minors":
            continue
        dr = sorted(sub.glob("*degree_requirements.json"))
        if not dr:
            continue
        prog = normalize_major(json.loads(dr[0].read_text()), sub.name)
        for gf in sorted(sub.glob("*general_education*.json")):
            ge = normalize_gened(json.loads(gf.read_text()))
            if ge:
                prog.root.children.append(ge)
        programs[prog.key] = prog

    minors_dir = base / "minors"
    if minors_dir.exists():
        for f in sorted(minors_dir.glob("cmu_minor_*.json")):
            p = normalize_minor(json.loads(f.read_text()), f.stem.replace("cmu_", "", 1))
            programs[p.key] = p

    return programs
