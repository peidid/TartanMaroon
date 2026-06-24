"""Storage-agnostic repository interface.

The advising tools depend only on this interface, so swapping the JSON-file
backend for MongoDB later is a config change, not a rewrite.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import networkx as nx

from ..models import Course, Offering
from ..requirements.models import Program


class Repository(ABC):
    @abstractmethod
    def get_course(self, code: str) -> Optional[Course]: ...

    @abstractmethod
    def get_program(self, key_or_name: str) -> Optional[Program]: ...

    @abstractmethod
    def list_programs(self) -> list[Program]: ...

    @abstractmethod
    def all_courses(self) -> dict[str, Course]: ...

    @abstractmethod
    def search_courses(self, query: str, limit: int = 10) -> list[Course]: ...

    @abstractmethod
    def offerings_for(self, code: str) -> list[Offering]: ...

    @abstractmethod
    def offerings_in(self, semester: str) -> list[Offering]: ...

    @abstractmethod
    def semesters(self) -> list[str]: ...

    @property
    @abstractmethod
    def prereq_graph(self) -> nx.DiGraph: ...
