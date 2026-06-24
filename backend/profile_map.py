"""Map a stored MongoDB user profile → the engine's StudentState."""

from __future__ import annotations

from advisor.etl.load_courses import normalize_code
from advisor.models import StudentState


def profile_to_student(profile: dict, name: str | None = None) -> StudentState:
    profile = profile or {}
    completed: dict[str, str | None] = {}
    in_progress: list[str] = []
    # Codes with no grade first, then overwrite with graded courses_taken.
    for code in profile.get("completed_courses", []) or []:
        if code:
            completed[normalize_code(code).upper()] = None
    for ct in profile.get("courses_taken", []) or []:
        code = (ct or {}).get("code")
        if not code:
            continue
        norm = normalize_code(code).upper()
        grade = (ct or {}).get("grade")
        # Grades "N" (no grade yet) / "IP" mark a course as currently in progress.
        if grade and grade.upper() in {"N", "IP"}:
            in_progress.append(norm)
            completed.pop(norm, None)
        else:
            completed[norm] = grade

    return StudentState(
        name=name,
        program=profile.get("major") or None,  # fuzzy-matched by repo.get_program
        year=profile.get("year") or None,
        gpa=profile.get("gpa"),
        minors=list(profile.get("minors", []) or []),
        concentration=profile.get("concentration") or None,
        expected_graduation=profile.get("expected_graduation") or None,
        completed=completed,
        in_progress=in_progress,
        interests=list(profile.get("interests", []) or []),
        career_goals=list(profile.get("career_goals", []) or []),
    )
