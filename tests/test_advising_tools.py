"""Deterministic tests for the advising tools (no LLM/API calls)."""

from __future__ import annotations

import pathlib

import pytest

from advisor.repository.json_repo import JsonRepository
from advisor.tools import advising

DATA = pathlib.Path(__file__).resolve().parents[1] / "data"


@pytest.fixture(scope="module")
def repo():
    return JsonRepository(DATA)


def test_course_details_known(repo):
    d = advising.course_details(repo, "15-122")
    assert d["code"] == "15-122"
    assert "Imperative" in d["name"]


def test_course_details_unknown(repo):
    assert "error" in advising.course_details(repo, "99-999")


def test_prerequisites_transitive(repo):
    d = advising.prerequisites(repo, "15-213")
    assert d["direct_prerequisites"] == ["15-122"]
    assert set(d["all_transitive_prerequisites"]) == {"15-112", "15-122"}


def test_eligibility_true_and_false(repo):
    ok = advising.check_eligibility(repo, "15-122", {"15-112": "A"})
    assert ok["eligible"] is True
    no = advising.check_eligibility(repo, "15-122", {})
    assert no["eligible"] is False
    assert "15-112" in no["referenced_but_not_completed"]


def test_eligibility_grade_threshold(repo):
    # 15-122 needs 15-112 at >= C; a D should fail.
    assert advising.check_eligibility(repo, "15-122", {"15-112": "D"})["eligible"] is False


def test_unlocks_nonempty(repo):
    d = advising.courses_unlocked_by(repo, "15-122")
    assert d["transitively_unlocks_count"] > 50


def test_offerings_and_is_offered(repo):
    assert advising.is_offered(repo, "15-122", "Spring 2026")["offered"] is True
    assert advising.is_offered(repo, "15-122", "Fall 1999")["offered"] is False


def test_code_normalization_no_dash(repo):
    assert advising.course_details(repo, "15122")["code"] == "15-122"
