"""Map a stored MongoDB user profile → the engine's StudentState."""

from __future__ import annotations

from advisor.etl.load_courses import normalize_code
from advisor.models import StudentState


def profile_to_student(profile: dict) -> StudentState:
    profile = profile or {}
    completed: dict[str, str | None] = {}
    # Codes with no grade first, then overwrite with graded courses_taken.
    for code in profile.get("completed_courses", []) or []:
        if code:
            completed[normalize_code(code).upper()] = None
    for ct in profile.get("courses_taken", []) or []:
        code = (ct or {}).get("code")
        if code:
            completed[normalize_code(code).upper()] = (ct or {}).get("grade")

    interests = list(profile.get("interests", []) or []) + list(profile.get("career_goals", []) or [])
    notes = (
        f"year={profile.get('year')}, gpa={profile.get('gpa')}, "
        f"minors={profile.get('minors')}, concentration={profile.get('concentration')}, "
        f"expected_graduation={profile.get('expected_graduation')}"
    )
    return StudentState(
        program=profile.get("major") or None,  # fuzzy-matched by repo.get_program
        completed=completed,
        interests=interests,
        notes=notes,
    )
