"""Tests for requirement normalization, CourseSet, and degree_progress."""

from __future__ import annotations

import pathlib

import pytest

from advisor.repository.json_repo import JsonRepository
from advisor.requirements.models import CourseSet
from advisor.requirements.progress import compute_progress

DATA = pathlib.Path(__file__).resolve().parents[1] / "data"


@pytest.fixture(scope="module")
def repo():
    return JsonRepository(DATA)


def _units(repo):
    return {c.code: (c.units or 0) for c in repo.all_courses().values()}


# ---- CourseSet predicate ----

def test_courseset_subject_and_exclusion():
    cs = CourseSet(subject_codes=["15"], excluded=["15-122"])
    assert cs.matches("15-213") is True
    assert cs.matches("15-122") is False     # excluded
    assert cs.matches("21-127") is False     # wrong subject


def test_courseset_range():
    cs = CourseSet(ranges=[("73", 300, 999)], excluded=["73-300"])
    assert cs.matches("73-365") is True
    assert cs.matches("73-300") is False     # excluded edge
    assert cs.matches("73-101") is False     # below range


# ---- normalization ----

def test_programs_loaded(repo):
    progs = {p.key for p in repo.list_programs()}
    assert "computer_science_ai" in progs
    assert "information_systems" in progs
    assert any(k.startswith("minor_") for k in progs)
    assert len(progs) >= 18


def test_cs_core_courses_normalized(repo):
    cs = repo.get_program("computer_science")
    leaf_courses = set()
    for leaf in cs.root.leaves():
        if leaf.course_set:
            leaf_courses |= set(leaf.course_set.explicit)
    assert {"15-122", "15-150", "15-210", "15-251"} <= leaf_courses


def test_is_constraint_captured(repo):
    is_prog = repo.get_program("information_systems")
    constraints = [c for leaf in is_prog.root.leaves() for c in leaf.constraints]
    assert any("15-121" in c or "15-122" in c for c in constraints)


# ---- progress ----

def test_progress_empty_student(repo):
    rep = compute_progress(repo.get_program("computer_science"), {}, _units(repo), list(repo.all_courses()))
    assert rep.overall_satisfied is False
    assert rep.unmet


def test_progress_credits_completed_core(repo):
    completed = {"15-122": "A", "15-150": "A", "15-210": "A", "15-251": "A"}
    rep = compute_progress(repo.get_program("computer_science"), completed, _units(repo), list(repo.all_courses()))
    # None of the four core courses should appear as unmet.
    joined = " ".join(rep.unmet)
    for core in ("15-122", "15-150", "15-210", "15-251"):
        assert f"take {core}" not in joined


def test_progress_single_use_assignment(repo):
    # 15-451 satisfies "Algorithm Design"; it must not also be double-counted.
    completed = {"15-451": "A"}
    rep = compute_progress(repo.get_program("computer_science"), completed, _units(repo), list(repo.all_courses()))
    applied_all = []

    def collect(rps):
        for rp in rps:
            applied_all.extend(rp.applied_courses)
            collect(rp.children)

    collect(rep.requirements)
    assert applied_all.count("15-451") == 1
