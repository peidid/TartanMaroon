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
        "completed_courses": ["15-112", "21-127"],
        "courses_taken": [{"code": "15122", "grade": "A"}, {"code": "15-150", "grade": "B"}],
        "interests": ["ML"], "career_goals": ["data scientist"],
    })
    assert student.program == "Computer Science"
    assert student.completed["15-122"] == "A"      # code normalized + graded
    assert student.completed["15-150"] == "B"
    assert student.completed["15-112"] is None      # completed_courses, no grade
    assert "data scientist" in student.interests
