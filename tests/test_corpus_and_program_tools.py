"""No-API tests for the prose corpus builder and program/requirement tools."""

from __future__ import annotations

import pathlib

import pytest

from advisor.repository.json_repo import JsonRepository
from advisor.retrieval.corpus import build_corpus
from advisor.tools import advising

DATA = pathlib.Path(__file__).resolve().parents[1] / "data"


@pytest.fixture(scope="module")
def repo():
    return JsonRepository(DATA)


# ---- corpus ----

def test_corpus_builds_and_is_bounded():
    chunks = build_corpus(DATA)
    assert len(chunks) > 800
    sources = {c.source.split("/")[0] for c in chunks}
    assert {"policies", "programs"} <= sources
    # markdown chunks are hard-wrapped; nothing absurdly large
    assert max(len(c.text) for c in chunks) <= 4000


# ---- program / requirement tools ----

def test_list_programs(repo):
    progs = advising.list_programs(repo)
    keys = {p["key"] for p in progs}
    assert "computer_science_ai" in keys
    assert any(k.startswith("minor_") for k in keys)


def test_program_requirements_structure(repo):
    pr = advising.program_requirements(repo, "computer_science")
    assert pr["kind"] == "major"
    assert pr["requirements"]["children"]            # has nested groups
    assert pr["total_units"]


def test_program_requirements_unknown(repo):
    pr = advising.program_requirements(repo, "underwater basket weaving")
    assert "error" in pr
    assert pr["available"]


def test_degree_progress_tool(repo):
    rep = advising.degree_progress(repo, "computer_science", {"15-122": "A", "15-150": "A"})
    assert rep["overall_satisfied"] is False
    assert isinstance(rep["unmet_requirements"], list) and rep["unmet_requirements"]
    assert "caveat" in rep
    # completed core courses are not reported as missing
    assert not any("take 15-122" in u for u in rep["unmet_requirements"])
