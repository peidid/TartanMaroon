"""No-API tests for program resolution aliases and profile→student mapping."""

from __future__ import annotations

import pathlib

import pytest

from advisor.repository.json_repo import JsonRepository
from backend.profile_map import profile_to_student

DATA = pathlib.Path(__file__).resolve().parents[1] / "data"


@pytest.fixture(scope="module")
def repo():
    return JsonRepository(DATA)


def test_program_aliases_resolve(repo):
    assert repo.get_program("cs").key == "computer_science_ai"
    assert repo.get_program("Computer Science").key == "computer_science_ai"
    assert repo.get_program("is").key == "information_systems"
    assert repo.get_program("computer_science").key == "computer_science_ai"


def test_short_substring_does_not_mismatch(repo):
    # "cs" must NOT fuzzy-match "Business Analytics" (analytiCS)
    assert repo.get_program("cs").kind == "major"
    assert "business" not in repo.get_program("cs").key


def test_unknown_program_returns_none(repo):
    assert repo.get_program("quidditch studies") is None


def test_profile_mapping():
    student = profile_to_student({
        "major": "Computer Science",
        "year": "Sophomore",
        "gpa": 3.6,
        "minors": ["Mathematics"],
        "completed_courses": ["15-112", "21-127"],
        "courses_taken": [
            {"code": "15122", "grade": "A"},
            {"code": "15-150", "grade": "B"},
            {"code": "15-213", "grade": "N"},   # no grade yet -> in progress
        ],
        "interests": ["ML"], "career_goals": ["data scientist"],
    }, name="Jane Doe")
    assert student.name == "Jane Doe"
    assert student.program == "Computer Science"
    assert student.year == "Sophomore"
    assert student.gpa == 3.6
    assert student.minors == ["Mathematics"]
    assert student.completed["15-122"] == "A"      # code normalized + graded
    assert student.completed["15-150"] == "B"
    assert student.completed["15-112"] is None      # completed_courses, no grade
    assert "15-213" in student.in_progress          # grade "N" -> in progress
    assert "15-213" not in student.completed
    assert student.interests == ["ML"]
    assert student.career_goals == ["data scientist"]


def test_profile_summary_personalization():
    """The profile must reach the agent as prompt text, not just internal state."""
    student = profile_to_student({
        "major": "Information Systems", "year": "Junior",
        "completed_courses": ["67-262"],
    }, name="Sam")
    summary = student.profile_summary()
    assert "Sam" in summary and "Information Systems" in summary and "67-262" in summary

    blank = profile_to_student({})
    assert not blank.has_profile()
    assert "none on file" in blank.profile_summary().lower()
