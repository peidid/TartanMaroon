"""No-API tests for the document library and program/requirement tools."""

from __future__ import annotations

import pathlib

import pytest

from advisor.repository.json_repo import JsonRepository
from advisor.retrieval.library import DocumentLibrary
from advisor.tools import advising

DATA = pathlib.Path(__file__).resolve().parents[1] / "data"


@pytest.fixture(scope="module")
def repo():
    return JsonRepository(DATA)


@pytest.fixture(scope="module")
def lib():
    return DocumentLibrary.build(DATA)


# ---- document library ----

def test_library_builds_with_catalog(lib):
    cat = lib.catalog()
    assert len(cat) > 50
    cats = {c["category"].split("/")[0] for c in cat}
    assert {"policies", "programs"} <= cats
    # every doc has locating metadata
    assert all(c["title"] and c["source"] for c in cat)
    # the redundant prereq dump is excluded
    assert not any("course_prerequisites" in c["source"] for c in cat)


def test_find_locates_changing_majors_doc(lib):
    hits = lib.find("how do I transfer into computer science", k=5)
    assert hits, "expected at least one match"
    assert "Policy_on_Changing_Majors" in hits[0]["source"]


def test_read_returns_full_cs_transfer_requirements(lib):
    """Regression: the CS row used to be sliced off at 'To be automatically acc…'."""
    doc = lib.read("programs/Policy_on_Changing_Majors_–_Scotty.md")
    text = doc["text"]
    assert not doc.get("truncated"), "small policy doc must not be truncated"
    # the actual transfer checklist must be present and readable
    assert "Computer Science" in text
    for code in ("21-127", "15-112", "21-120"):
        assert code in text
    assert "3.6" in text  # required QPA in the course set


def test_read_unknown_document(lib):
    res = lib.read("does/not/exist.md")
    assert "error" in res


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
