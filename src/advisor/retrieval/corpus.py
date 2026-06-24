"""Build a chunked prose corpus from the markdown + advising-doc sources.

Covers ``policies/``, ``student_life/``, ``academics/``, and the advising/
requirement markdown under ``programs/``, plus the ``CMUQ_BS_Advising_Document``
JSON (an array of ``{Subheading, Content, Tags}``). Markdown is split on
headings; embedded HTML, breadcrumbs, and page footers are stripped. PDFs are
skipped (noted to the user).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import BaseModel

_PROSE_DIRS = ["policies", "student_life", "academics", "programs"]
_MAX_CHARS = 1600

_HTML = re.compile(r"<[^>]+>")
_HEADING = re.compile(r"^(#{1,4})\s+(.*)$")
_DROP_LINE = re.compile(
    r"^\s*(page owner|last updated|home\s*[/›»]|.*\s[/›»]\s.*scotty\s*$)",
    re.IGNORECASE,
)


class Chunk(BaseModel):
    id: str
    source: str          # path relative to data/
    title: str           # heading trail / subheading
    text: str


def _clean(text: str) -> str:
    out = []
    for line in text.splitlines():
        line = _HTML.sub(" ", line).rstrip()
        if _DROP_LINE.match(line):
            continue
        out.append(line)
    return "\n".join(out)


def _split_long(title: str, body: str) -> list[str]:
    body = body.strip()
    if len(body) <= _MAX_CHARS:
        return [body] if body else []
    parts, cur = [], ""
    for para in body.split("\n\n"):
        if len(cur) + len(para) > _MAX_CHARS and cur:
            parts.append(cur.strip())
            cur = ""
        cur += para + "\n\n"
    if cur.strip():
        parts.append(cur.strip())
    # Hard-wrap any part that is still oversized (a single huge paragraph/table).
    wrapped: list[str] = []
    for part in parts:
        while len(part) > _MAX_CHARS:
            wrapped.append(part[:_MAX_CHARS])
            part = part[_MAX_CHARS:]
        if part.strip():
            wrapped.append(part)
    return wrapped


def chunk_markdown(rel_source: str, text: str) -> list[Chunk]:
    text = _clean(text)
    chunks: list[Chunk] = []
    trail: list[str] = []
    cur_title = Path(rel_source).stem.replace("_", " ")
    buf: list[str] = []

    def flush():
        body = "\n".join(buf).strip()
        title = " › ".join(trail) if trail else cur_title
        for i, part in enumerate(_split_long(title, body)):
            chunks.append(Chunk(
                id=f"{rel_source}#{len(chunks)}",
                source=rel_source, title=title, text=part,
            ))

    for line in text.splitlines():
        m = _HEADING.match(line)
        if m:
            flush()
            buf = []
            level = len(m.group(1))
            trail = trail[: level - 1] + [m.group(2).strip()]
        else:
            buf.append(line)
    flush()
    return [c for c in chunks if len(c.text) > 40]


def chunk_advising_json(rel_source: str, data) -> list[Chunk]:
    chunks = []
    if not isinstance(data, list):
        return chunks
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        title = item.get("Subheading") or item.get("subheading") or f"section {i}"
        content = item.get("Content") or item.get("content") or ""
        tags = item.get("Tags") or item.get("tags") or ""
        text = _clean(f"{content}\n\nTags: {tags}".strip())
        if len(text) > 40:
            chunks.append(Chunk(id=f"{rel_source}#{i}", source=rel_source, title=str(title), text=text))
    return chunks


def build_corpus(data_dir: str | Path) -> list[Chunk]:
    base = Path(data_dir)
    chunks: list[Chunk] = []
    for d in _PROSE_DIRS:
        root = base / d
        if not root.exists():
            continue
        for p in sorted(root.rglob("*.md")):
            rel = str(p.relative_to(base))
            chunks.extend(chunk_markdown(rel, p.read_text(errors="ignore")))
    # advising-document JSONs
    for p in sorted(base.glob("programs/**/*Advising_Document.json")):
        rel = str(p.relative_to(base))
        try:
            chunks.extend(chunk_advising_json(rel, json.loads(p.read_text())))
        except json.JSONDecodeError:
            pass
    return chunks
