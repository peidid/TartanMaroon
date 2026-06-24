"""In-memory repository backed by the raw ``data/`` JSON files.

Loads everything once at construction (the dataset is small — ~2.5k courses),
parses prereqs, and builds the prereq DAG. A future ``MongoRepository`` will
implement the same :class:`Repository` interface.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Optional

import networkx as nx

from ..etl.load_courses import load_courses, normalize_code
from ..etl.load_offerings import load_offerings
from ..graph.build import build_prereq_dag
from ..models import Course, Offering
from ..requirements.models import Program
from ..requirements.normalize import load_programs
from .base import Repository


def _canon(code: str) -> str:
    return normalize_code(code).upper()


class JsonRepository(Repository):
    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self._courses: dict[str, Course] = load_courses(self.data_dir)
        self._graph: nx.DiGraph = build_prereq_dag(self._courses)

        self._offerings_by_course: dict[str, list[Offering]] = defaultdict(list)
        self._offerings_by_sem: dict[str, list[Offering]] = defaultdict(list)
        for off in load_offerings(self.data_dir):
            self._offerings_by_course[off.course_code].append(off)
            self._offerings_by_sem[off.semester].append(off)

        self._programs: dict[str, Program] = load_programs(self.data_dir)

    def get_course(self, code: str) -> Optional[Course]:
        return self._courses.get(_canon(code))

    def all_courses(self) -> dict[str, Course]:
        return self._courses

    def search_courses(self, query: str, limit: int = 10) -> list[Course]:
        q = query.strip().lower()
        if not q:
            return []
        scored: list[tuple[int, Course]] = []
        for c in self._courses.values():
            hay = f"{c.code} {c.name} {c.short_name or ''} {c.long_desc or ''}".lower()
            if q in hay:
                # Prefer code/name hits over description hits.
                score = 0 if q in c.code.lower() else 1 if q in c.name.lower() else 2
                scored.append((score, c))
        scored.sort(key=lambda t: (t[0], t[1].code))
        return [c for _, c in scored[:limit]]

    def offerings_for(self, code: str) -> list[Offering]:
        return list(self._offerings_by_course.get(_canon(code), []))

    def offerings_in(self, semester: str) -> list[Offering]:
        return list(self._offerings_by_sem.get(semester, []))

    def semesters(self) -> list[str]:
        return sorted(self._offerings_by_sem.keys())

    _PROGRAM_ALIASES = {
        "cs": "computer_science_ai",
        "computer science": "computer_science_ai",
        "is": "information_systems",
        "information systems": "information_systems",
        "ba": "business_administration",
        "business administration": "business_administration",
        "bio": "biological_science",
        "biology": "biological_science",
        "biological sciences": "biological_science",
    }

    def get_program(self, key_or_name: str) -> Optional[Program]:
        q = key_or_name.strip().lower()
        if not q:
            return None
        qs = q.replace("_", " ")
        # 1. exact key (either separator form)
        if q in self._programs:
            return self._programs[q]
        for p in self._programs.values():
            if p.key.lower() in (q, qs.replace(" ", "_")):
                return p
        # 2. known abbreviations / common names
        alias = self._PROGRAM_ALIASES.get(qs)
        if alias and alias in self._programs:
            return self._programs[alias]
        # 3. substring on name/key, but only for queries long enough to be
        #    unambiguous (avoids "cs" matching "analytiCS", "is" matching ...)
        if len(qs) >= 4:
            for p in self._programs.values():
                if qs in p.name.lower() or qs in p.key.lower().replace("_", " "):
                    return p
        # 4. key prefix
        for p in self._programs.values():
            if p.key.lower().startswith(qs.replace(" ", "_")):
                return p
        return None

    def list_programs(self) -> list[Program]:
        return list(self._programs.values())

    @property
    def prereq_graph(self) -> nx.DiGraph:
        return self._graph
