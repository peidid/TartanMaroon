"""Compute degree progress against a normalized program.

Assignment is greedy with **single use within a program**: each completed course
counts toward at most one requirement, and more-specific buckets (named courses,
small explicit choices) claim courses before broad subject/range pools — so a
core course isn't "spent" on a generic elective. Cross-program double-counting
(e.g. "up to 2 courses may double count") is a separate policy surfaced verbatim
in the report, not enforced here. This is an honest estimate, not a registrar
audit — the exact constrained-matching is reserved for the solver phase.
"""

from __future__ import annotations

from typing import Optional

from ..prereqs.ast import grade_meets
from .models import Program, ProgressReport, Requirement, RequirementProgress


def _specificity(leaf: Requirement):
    cs = leaf.course_set
    if leaf.kind == "course":
        return (0, 1, 0)
    if cs and cs.is_predicate():
        return (2, 9999, -(leaf.n or 0))
    size = len(cs.explicit) if cs else 9999
    return (1, size, -(leaf.n or 0))


def compute_progress(
    program: Program,
    completed: dict[str, Optional[str]],
    course_units: dict[str, float],
    all_codes: list[str],
) -> ProgressReport:
    leaves = program.root.leaves()
    assignable = [l for l in leaves if l.kind in ("course", "choose", "units")]
    used: set[str] = set()
    result: dict[int, dict] = {}

    for leaf in sorted(assignable, key=_specificity):
        cs = leaf.course_set
        eligible = [
            c for c in completed
            if cs and cs.matches(c) and c not in used and grade_meets(completed.get(c), leaf.min_grade)
        ]
        if leaf.kind == "course":
            applied = eligible[:1]
            satisfied = bool(applied)
        elif leaf.kind == "choose":
            need = leaf.n or 1
            applied = eligible[:need]
            satisfied = len(applied) >= need
        else:  # units
            applied, total = [], 0.0
            for c in eligible:
                applied.append(c)
                total += course_units.get(c, 0) or 0
                if total >= (leaf.min_units or 0):
                    break
            satisfied = total >= (leaf.min_units or 0)
        used |= set(applied)
        result[id(leaf)] = {"satisfied": satisfied, "applied": applied}

    manual_review: list[str] = []
    unmet: list[str] = []

    def examples(leaf: Requirement) -> list[str]:
        if not leaf.course_set:
            return []
        return [c for c in leaf.course_set.resolve(all_codes) if c not in completed][:6]

    def build(req: Requirement) -> RequirementProgress:
        if req.kind == "note":
            manual_review.append(req.name)
            return RequirementProgress(
                name=req.name, kind="note", satisfied=True,
                needed="manual review", remaining=req.note,
            )
        if req.kind in ("course", "choose", "units"):
            r = result.get(id(req), {"satisfied": False, "applied": []})
            cs_desc = req.course_set.describe() if req.course_set else ""
            if req.kind == "course":
                needed = "required"
            elif req.kind == "choose":
                needed = f"choose {req.n or 1} from {cs_desc}"
            else:
                needed = f"{req.min_units:g} units from {cs_desc}"
            rp = RequirementProgress(
                name=req.name, kind=req.kind, satisfied=r["satisfied"],
                needed=needed, applied_courses=r["applied"],
            )
            if not r["satisfied"]:
                if req.kind == "choose":
                    rp.remaining = f"{(req.n or 1) - len(r['applied'])} more from {cs_desc}"
                elif req.kind == "course":
                    rp.remaining = f"take {req.course_set.explicit[0] if req.course_set.explicit else '?'}"
                else:
                    rp.remaining = f"more units from {cs_desc}"
                rp.eligible_examples = examples(req)
                unmet.append(f"{req.name} — {rp.remaining}")
            if req.constraints:
                rp.needed += f"  ({'; '.join(req.constraints)})"
            return rp
        # group
        kids = [build(c) for c in req.children]
        if req.kind == "choose":
            need = req.n or 1
            sat = sum(1 for k in kids if k.satisfied) >= need
            needed = f"complete {need} of {len(kids)}"
        else:
            sat = all(k.satisfied for k in kids) if kids else True
            needed = "complete all"
        return RequirementProgress(name=req.name, kind=req.kind, satisfied=sat,
                                   needed=needed, children=kids)

    tree = build(program.root)
    n_leaves = len([l for l in leaves if l.kind != "note"])
    n_met = sum(1 for l in assignable if result.get(id(l), {}).get("satisfied"))
    units_done = sum(course_units.get(c, 0) or 0 for c in used)

    summary = f"{n_met}/{n_leaves} graded requirements met"
    if program.total_units:
        summary += f"; ~{units_done:g}/{program.total_units:g} units applied"

    caveat = (
        "Estimate only (single-use-within-program assignment); not a registrar audit. "
    )
    if manual_review:
        caveat += f"Manual review needed: {', '.join(manual_review)}. "
    if program.double_counting_rules:
        caveat += "Cross-program double-counting follows the program's stated rules (see double_counting)."

    return ProgressReport(
        program=program.name,
        overall_satisfied=(not unmet),
        summary=summary,
        requirements=tree.children or [tree],
        unmet=unmet,
        caveat=caveat,
    )
