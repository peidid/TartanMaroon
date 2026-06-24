"""Agentic document library for the handbook / policy / advising prose.

Replaces the old chunk-and-embed RAG path. The prose corpus is small (~100
files, ~1MB), so instead of slicing it into embedded chunks — which split tables
and truncated answers — we give the agent three deterministic tools:

* ``list_documents`` — the full catalog (title + category + summary) so the
  agent can *browse* and reason about which document is relevant.
* ``find_documents`` — full-text keyword search returning ranked candidates,
  each with a context snippet, so the agent can *locate* precisely.
* ``read_document`` — the *entire* cleaned document (HTML tables rendered as
  readable rows), so the agent can quote exact requirements.

The library is built in memory from the files on first use (cheap, always fresh
— no embedding cache to rebuild or to go stale).
"""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

# Prose lives in these top-level data dirs (course/program *structured* JSON is
# handled by the repository, not here).
_PROSE_DIRS = ["policies", "student_life", "academics", "programs"]

# Files that are redundant with the structured backbone or are pure data dumps —
# excluded so reads stay focused and cheap.
_EXCLUDE = {"programs/course_prerequisites.md"}

_MAX_READ_CHARS = 40_000  # generous per-read window; docs are smaller than this

_HTML_TAG = re.compile(r"<[^>]+>")
_HEADING = re.compile(r"^(#{1,4})\s+(.*)$")
_DROP_LINE = re.compile(
    r"^\s*(page owner|last updated|home\s*[/›»]|.*\s[/›»]\s.*scotty\s*$)",
    re.IGNORECASE,
)
_WORD = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")  # words + course codes like 15-112
_COURSE = re.compile(r"\b\d{2}-\d{3}\b")

# Light query aliasing so common advising phrasings still locate the right doc
# even when the document uses different words.
_ALIASES: dict[str, list[str]] = {
    "cs": ["computer", "science"],
    "ai": ["artificial", "intelligence"],
    "is": ["information", "systems"],
    "ba": ["business", "administration"],
    "bio": ["biological", "biology"],
    "transfer": ["transfer", "changing", "change", "major"],
    "switch": ["transfer", "changing", "change", "major"],
    "overload": ["overload", "course", "load", "units"],
    "minor": ["minor", "minors"],
    "gpa": ["gpa", "qpa"],
    "qpa": ["qpa", "gpa"],
    "drop": ["drop", "withdraw", "withdrawal"],
    "appeal": ["appeal", "grade", "grievance"],
    "graduate": ["graduation", "degree", "requirements"],
}


def _unescape(text: str) -> str:
    return html.unescape(text).replace("\xa0", " ")


def _clean(text: str) -> str:
    """Strip boilerplate and render HTML tables as readable ' | '-separated rows."""
    # Render table structure BEFORE removing tags so rows/cells survive.
    text = re.sub(r"</t[dh]\s*>", " | ", text, flags=re.IGNORECASE)
    text = re.sub(r"</tr\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<(tr|table|tbody|thead)\b[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = _HTML_TAG.sub(" ", text)
    text = _unescape(text)
    out: list[str] = []
    for line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", line).strip(" |").rstrip()
        if not line or _DROP_LINE.match(line):
            continue
        out.append(line)
    # collapse runs of blank lines (already filtered empties, so just join)
    return "\n".join(out)


def _tokenize(text: str) -> list[str]:
    toks = [w for w in _WORD.findall(text.lower()) if len(w) > 2 or "-" in w]
    return toks


def _expand(tokens: list[str]) -> set[str]:
    out: set[str] = set()
    for t in tokens:
        out.add(t)
        out.update(_ALIASES.get(t, []))
    return out


class DocMeta(BaseModel):
    source: str            # path relative to data/, e.g. "programs/Policy_on_Changing_Majors_–_Scotty.md"
    title: str
    category: str          # e.g. "programs", "policies/registration"
    summary: str           # lead text, for browsing
    headings: list[str]    # section outline (markdown headings / advising subheadings)
    n_chars: int


class _Doc:
    def __init__(self, meta: DocMeta, text: str):
        self.meta = meta
        self.text = text
        self.lower = text.lower()
        self.title_lower = meta.title.lower()
        self.head_lower = " \n ".join(meta.headings).lower()


def _category(rel: str) -> str:
    parts = Path(rel).parts
    return "/".join(parts[:2]) if len(parts) > 2 else parts[0]


def _md_to_doc(rel: str, raw: str) -> _Doc:
    text = _clean(raw)
    headings: list[str] = []
    title = ""
    body_lines: list[str] = []
    for line in text.splitlines():
        m = _HEADING.match(line)
        if m:
            h = m.group(2).strip()
            headings.append(h)
            if not title:
                title = h
        else:
            body_lines.append(line)
    if not title:
        title = Path(rel).stem.replace("_", " ").replace("–", "-").strip()
    body = "\n".join(body_lines).strip()
    summary = re.sub(r"\s+", " ", body)[:240].strip()
    meta = DocMeta(source=rel, title=title, category=_category(rel),
                   summary=summary, headings=headings[:25], n_chars=len(text))
    return _Doc(meta, text)


def _advising_json_to_doc(rel: str, data) -> Optional[_Doc]:
    if not isinstance(data, list):
        return None
    headings, sections = [], []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        sub = item.get("Subheading") or item.get("subheading") or f"section {i}"
        content = item.get("Content") or item.get("content") or ""
        tags = item.get("Tags") or item.get("tags") or ""
        headings.append(str(sub))
        block = _clean(f"## {sub}\n{content}" + (f"\nTags: {tags}" if tags else ""))
        sections.append(block)
    if not sections:
        return None
    text = "\n\n".join(sections)
    title = Path(rel).stem.replace("_", " ").strip()
    summary = re.sub(r"\s+", " ", _clean(str(data[0].get("Content", "")) if isinstance(data[0], dict) else ""))[:240]
    meta = DocMeta(source=rel, title=title, category=_category(rel),
                   summary=summary or title, headings=headings[:25], n_chars=len(text))
    return _Doc(meta, text)


class DocumentLibrary:
    def __init__(self, docs: list[_Doc]):
        self._docs = docs
        self._by_source = {d.meta.source: d for d in docs}

    @classmethod
    def build(cls, data_dir: str | Path) -> "DocumentLibrary":
        base = Path(data_dir)
        docs: list[_Doc] = []
        for d in _PROSE_DIRS:
            root = base / d
            if not root.exists():
                continue
            for p in sorted(root.rglob("*.md")):
                rel = str(p.relative_to(base))
                if rel in _EXCLUDE:
                    continue
                doc = _md_to_doc(rel, p.read_text(errors="ignore"))
                if doc.meta.n_chars > 40:
                    docs.append(doc)
        for p in sorted(base.glob("programs/**/*Advising_Document.json")):
            rel = str(p.relative_to(base))
            try:
                import json
                doc = _advising_json_to_doc(rel, json.loads(p.read_text()))
                if doc and doc.meta.n_chars > 40:
                    docs.append(doc)
            except (ValueError, OSError):
                pass
        return cls(docs)

    # ---- catalog ----
    def catalog(self, category: str = "") -> list[dict]:
        cat = category.lower().strip()
        items = []
        for d in self._docs:
            if cat and cat not in d.meta.category.lower() and cat not in d.meta.title.lower():
                continue
            items.append({
                "source": d.meta.source,
                "title": d.meta.title,
                "category": d.meta.category,
                "summary": d.meta.summary[:160],
            })
        return sorted(items, key=lambda x: (x["category"], x["title"]))

    # ---- search ----
    def find(self, query: str, k: int = 5) -> list[dict]:
        terms = _expand(_tokenize(query))
        codes = set(_COURSE.findall(query))
        q_norm = re.sub(r"\s+", " ", query.lower()).strip()
        scored: list[tuple[float, _Doc]] = []
        for d in self._docs:
            score = 0.0
            for t in terms:
                if t in d.title_lower:
                    score += 6
                if t in d.head_lower:
                    score += 3
                c = d.lower.count(t)
                if c:
                    score += 1 + min(c, 5) * 0.4   # presence + capped frequency
            for code in codes:
                score += 4 * d.text.count(code)
            if len(q_norm) > 8 and q_norm in d.lower:
                score += 8                          # exact phrase bonus
            if score > 0:
                scored.append((score, d))
        scored.sort(key=lambda x: x[0], reverse=True)
        out = []
        for score, d in scored[:k]:
            out.append({
                "source": d.meta.source,
                "title": d.meta.title,
                "category": d.meta.category,
                "score": round(score, 1),
                "headings": d.meta.headings[:12],
                "snippet": self._snippet(d, terms | codes),
            })
        return out

    @staticmethod
    def _snippet(d: _Doc, terms: set[str], width: int = 420) -> str:
        pos = -1
        for t in sorted(terms, key=len, reverse=True):
            p = d.lower.find(t.lower())
            if p != -1:
                pos = p
                break
        if pos == -1:
            return d.meta.summary
        start = max(0, pos - width // 3)
        end = min(len(d.text), start + width)
        snip = d.text[start:end].strip()
        return ("…" if start > 0 else "") + snip + ("…" if end < len(d.text) else "")

    # ---- read ----
    def read(self, source: str, offset: int = 0) -> dict:
        d = self._by_source.get(source)
        if d is None:  # fuzzy fallback: basename / title / substring
            s = source.lower().strip()
            cands = [doc for doc in self._docs
                     if s in doc.meta.source.lower() or s in doc.meta.title.lower()
                     or Path(doc.meta.source).stem.lower() == s]
            if len(cands) == 1:
                d = cands[0]
            elif len(cands) > 1:
                return {"error": f"'{source}' is ambiguous",
                        "candidates": [c.meta.source for c in cands[:8]]}
        if d is None:
            return {"error": f"document '{source}' not found",
                    "hint": "use find_documents or list_documents to get an exact source"}
        offset = max(0, offset)
        window = d.text[offset:offset + _MAX_READ_CHARS]
        more = offset + _MAX_READ_CHARS < len(d.text)
        result = {
            "source": d.meta.source,
            "title": d.meta.title,
            "category": d.meta.category,
            "text": window,
        }
        if more:
            result["truncated"] = True
            result["next_offset"] = offset + _MAX_READ_CHARS
            result["total_chars"] = len(d.text)
        return result


_LIBRARY: Optional[DocumentLibrary] = None


def get_library(data_dir: str | Path | None = None) -> DocumentLibrary:
    global _LIBRARY
    if _LIBRARY is None:
        from ..config import settings
        _LIBRARY = DocumentLibrary.build(data_dir or settings.data_dir)
    return _LIBRARY


def list_documents(category: str = "") -> list[dict]:
    return get_library().catalog(category)


def find_documents(query: str, k: int = 5) -> list[dict]:
    return get_library().find(query, k)


def read_document(source: str, offset: int = 0) -> dict:
    return get_library().read(source, offset)
