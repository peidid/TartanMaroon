"""Deterministic advising tools over the structured backbone.

These are plain functions (no LLM) returning JSON-serializable results, so they
are unit-testable on their own. ``agent.py`` registers thin wrappers around
them as Pydantic AI tools.
"""

from __future__ import annotations

from typing import Optional

from ..graph.build import prereq_closure, unlocks
from ..repository.base import Repository
from ..requirements.progress import compute_progress


def find_courses(repo: Repository, query: str, limit: int = 10) -> list[dict]:
    """Search courses by code, title, or description keyword."""
    return [
        {"code": c.code, "name": c.name, "units": c.units}
        for c in repo.search_courses(query, limit=limit)
    ]


def course_details(repo: Repository, code: str) -> dict:
    """Full detail for one course."""
    c = repo.get_course(code)
    if not c:
        return {"error": f"No course found with code {code!r}."}
    desc = (c.long_desc or "")[:500]
    return {
        "code": c.code,
        "name": c.name,
        "units": c.units,
        "department": c.dept,
        "prerequisites": c.prereq_ast.describe() if c.prereq_ast else "none",
        "corequisites": [r.code for r in c.co_reqs],
        "anti_requisites": [r.code for r in c.anti_reqs],
        "cross_listed_equiv": [r.code for r in c.equiv],
        "description": desc,
        "website": c.website,
    }


def prerequisites(repo: Repository, code: str) -> dict:
    """Direct and full transitive prerequisites of a course."""
    c = repo.get_course(code)
    if not c:
        return {"error": f"No course found with code {code!r}."}
    g = repo.prereq_graph
    return {
        "code": c.code,
        "prerequisite_expression": c.prereq_ast.describe() if c.prereq_ast else "none",
        "direct_prerequisites": sorted(c.direct_prereq_courses()),
        "all_transitive_prerequisites": sorted(prereq_closure(g, c.code)),
    }


def check_eligibility(repo: Repository, code: str, completed: dict[str, Optional[str]]) -> dict:
    """Is a student (given their completed courses+grades) eligible for a course?"""
    c = repo.get_course(code)
    if not c:
        return {"error": f"No course found with code {code!r}."}
    if not c.prereq_ast:
        return {"code": c.code, "eligible": True, "reason": "No prerequisites."}
    eligible = c.prereq_ast.satisfied_by(completed)
    referenced = sorted(c.prereq_ast.referenced_courses())
    not_taken = [pre for pre in referenced if pre not in completed]
    return {
        "code": c.code,
        "eligible": eligible,
        "prerequisite_expression": c.prereq_ast.describe(),
        "referenced_courses": referenced,
        "referenced_but_not_completed": not_taken,
    }


def courses_unlocked_by(repo: Repository, code: str) -> dict:
    """What a course is a prerequisite for (directly and transitively)."""
    g = repo.prereq_graph
    if code.upper() not in g and not repo.get_course(code):
        return {"error": f"No course found with code {code!r}."}
    canon = repo.get_course(code).code if repo.get_course(code) else code.upper()
    transitive = sorted(unlocks(g, canon))
    return {
        "code": canon,
        "directly_unlocks": sorted(g.successors(canon)) if canon in g else [],
        "transitively_unlocks_count": len(transitive),
        "transitively_unlocks_sample": transitive[:25],
    }


def course_offerings(repo: Repository, code: str) -> list[dict]:
    """All known scheduled sections of a course across loaded semesters."""
    return [
        {
            "semester": o.semester,
            "section": o.section,
            "days": o.days,
            "start_time": o.start_time,
            "end_time": o.end_time,
            "instructor": o.instructor,
        }
        for o in repo.offerings_for(code)
    ]


def is_offered(repo: Repository, code: str, semester: str) -> dict:
    """Was/is a course offered in a given semester (e.g. 'Spring 2026')?"""
    sections = [o for o in repo.offerings_for(code) if o.semester.lower() == semester.lower()]
    return {
        "code": repo.get_course(code).code if repo.get_course(code) else code,
        "semester": semester,
        "offered": bool(sections),
        "sections": [{"section": o.section, "instructor": o.instructor, "days": o.days} for o in sections],
        "known_semesters": repo.semesters(),
    }


def list_semesters(repo: Repository) -> list[str]:
    """Semesters for which schedule data is loaded."""
    return repo.semesters()


# ---- programs & degree requirements ----

def list_programs(repo: Repository) -> list[dict]:
    """All majors and minors with their lookup keys."""
    return [{"key": p.key, "name": p.name, "kind": p.kind} for p in repo.list_programs()]


def _req_node(r, depth: int, maxdepth: int) -> dict:
    d: dict = {"name": r.name, "kind": r.kind}
    if r.n:
        d["choose"] = r.n
    if r.min_units:
        d["units"] = r.min_units
    if r.course_set and r.kind in ("course", "choose", "units"):
        d["from"] = r.course_set.describe()
    if r.constraints:
        d["constraints"] = r.constraints
    if r.note:
        d["note"] = r.note
    if r.children and depth < maxdepth:
        d["children"] = [_req_node(c, depth + 1, maxdepth) for c in r.children]
    return d


def program_requirements(repo: Repository, program: str) -> dict:
    """The normalized requirement structure of a program (for browsing)."""
    p = repo.get_program(program)
    if not p:
        return {"error": f"No program matching {program!r}.",
                "available": [x["key"] for x in list_programs(repo)]}
    return {
        "program": p.name, "kind": p.kind, "total_units": p.total_units,
        "double_counting_rules": p.double_counting_rules,
        "requirements": _req_node(p.root, 0, 3),
    }


def degree_progress(repo: Repository, program: str, completed: dict[str, Optional[str]]) -> dict:
    """Compute what a student still needs for a program, given completed courses."""
    p = repo.get_program(program)
    if not p:
        return {"error": f"No program matching {program!r}.",
                "available": [x["key"] for x in list_programs(repo)]}
    units = {c.code: (c.units or 0) for c in repo.all_courses().values()}
    rep = compute_progress(p, completed, units, list(repo.all_courses()))
    return {
        "program": rep.program,
        "overall_satisfied": rep.overall_satisfied,
        "summary": rep.summary,
        "unmet_requirements": rep.unmet,
        "top_level": [
            {"name": r.name, "satisfied": r.satisfied, "needed": r.needed}
            for r in rep.requirements
        ],
        "double_counting_rules": p.double_counting_rules,
        "caveat": rep.caveat,
    }
