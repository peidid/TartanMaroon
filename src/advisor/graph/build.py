"""Build and query the prerequisite DAG with networkx.

Edges point prereq -> dependent course, so:
- ancestors(code)   = the full set of courses that must (transitively) precede it
- descendants(code) = everything that course transitively unlocks
"""

from __future__ import annotations

import networkx as nx

from ..models import Course


def build_prereq_dag(courses: dict[str, Course]) -> nx.DiGraph:
    g = nx.DiGraph()
    for code, c in courses.items():
        g.add_node(code, name=c.name, in_catalog=True)
    for code, c in courses.items():
        for pre in c.direct_prereq_courses():
            if pre == code:
                # Catalog data quirk: a course listing itself as a prereq
                # (e.g. 15-295). Skip to keep the graph acyclic.
                continue
            if pre not in g:
                # Referenced but not a catalog file (cross-listed / retired).
                g.add_node(pre, name=None, in_catalog=False)
            g.add_edge(pre, code)
    return g


def prereq_closure(g: nx.DiGraph, code: str) -> set[str]:
    """All courses that transitively must come before ``code``."""
    return set(nx.ancestors(g, code)) if code in g else set()


def unlocks(g: nx.DiGraph, code: str) -> set[str]:
    """All courses ``code`` is (transitively) a prerequisite for."""
    return set(nx.descendants(g, code)) if code in g else set()


def direct_unlocks(g: nx.DiGraph, code: str) -> list[str]:
    return sorted(g.successors(code)) if code in g else []


def longest_prereq_chain(g: nx.DiGraph) -> list[str]:
    """Longest dependency path in the DAG (a complexity signal)."""
    if not nx.is_directed_acyclic_graph(g):
        return []
    return nx.dag_longest_path(g)
