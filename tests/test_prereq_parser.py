"""Validate the prereq parser against the full real catalog.

The headline assertion is the feasibility number: essentially every non-empty
prereq string in the catalog must parse into an AST. If this regresses, the DAG
backbone is no longer safe to build from parsed prereqs.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from advisor.prereqs.ast import Atom, And, Or
from advisor.prereqs.parser import parse_prereqs

DATA = pathlib.Path(__file__).resolve().parents[1] / "data" / "courses"


def _all_prereq_texts() -> list[tuple[str, str]]:
    out = []
    for p in sorted(DATA.glob("*.json")):
        d = json.loads(p.read_text())
        text = ((d.get("prereqs") or {}).get("text") or "").strip()
        if text:
            out.append((p.stem, text))
    return out


def test_parses_essentially_all_real_prereqs():
    texts = _all_prereq_texts()
    assert texts, "no course data found — is data/courses populated?"
    failures = [(code, t) for code, t in texts if parse_prereqs(t) is None]
    rate = 1 - len(failures) / len(texts)
    # Print a few failures to aid debugging if this ever regresses.
    assert rate >= 0.99, f"only {rate:.1%} parsed; failures: {failures[:10]}"


def test_referenced_courses_are_recoverable():
    texts = _all_prereq_texts()
    for code, t in texts:
        expr = parse_prereqs(t)
        if expr is None:
            continue
        refs = expr.referenced_courses()
        assert refs, f"{code}: parsed but referenced no courses"
        assert all("-" in c for c in refs)


def test_simple_atom_with_grade():
    expr = parse_prereqs("15-112 [] at least C")
    assert isinstance(expr, Atom)
    assert expr.course == "15-112"
    assert expr.min_grade == "C"


def test_nested_and_or_structure():
    # 15-122's real-world neighbours: an OR of two courses, ANDed with another.
    expr = parse_prereqs(
        "((15-122 [] at least C) or (15-121 [] at least C)) and (21-127 [] at least C)"
    )
    assert isinstance(expr, And)
    assert len(expr.children) == 2
    left = expr.children[0]
    assert isinstance(left, Or)
    assert {a.course for a in left.children} == {"15-122", "15-121"}


def test_grade_threshold_evaluation():
    expr = parse_prereqs("15-112 [] at least C")
    assert expr.satisfied_by({"15-112": "B"}) is True   # B >= C
    assert expr.satisfied_by({"15-112": "C"}) is True
    assert expr.satisfied_by({"15-112": "D"}) is False  # D < C
    assert expr.satisfied_by({}) is False               # not taken


def test_qatar_course_code_format():
    expr = parse_prereqs("QC-211 [] at least D")
    assert isinstance(expr, Atom)
    assert expr.course == "QC-211"


def test_empty_and_none():
    assert parse_prereqs("") is None
    assert parse_prereqs(None) is None
    assert parse_prereqs("   ") is None


@pytest.mark.parametrize("expr_text,completed,expected", [
    ("(15-112 [] at least C) or (15-110 [] at least C)", {"15-110": "A"}, True),
    ("(15-112 [] at least C) and (21-127 [] at least C)", {"15-112": "A"}, False),
])
def test_and_or_evaluation(expr_text, completed, expected):
    assert parse_prereqs(expr_text).satisfied_by(completed) is expected
