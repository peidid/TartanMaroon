"""Hybrid (embedding + keyword) retrieval over the prose corpus.

The index caches embeddings to ``.advisor_cache/`` so it is built once. Search
combines cosine similarity with a lightweight keyword-overlap score, which helps
exact-term queries (course codes, policy names) that pure embeddings can miss.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

import numpy as np

from ..config import settings
from .corpus import Chunk, build_corpus
from .embed import embed_query, embed_texts

_CACHE = Path(".advisor_cache")
_VECS = _CACHE / "prose_vectors.npy"
_META = _CACHE / "prose_chunks.json"
_WORD = re.compile(r"[a-z0-9\-]+")


def _keywords(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if len(w) > 2}


class ProseIndex:
    def __init__(self, chunks: list[Chunk], vectors: np.ndarray):
        self.chunks = chunks
        self.vectors = vectors
        self._kw = [_keywords(c.title + " " + c.text) for c in chunks]

    # ---- persistence ----
    @classmethod
    def build(cls, data_dir: str | Path) -> "ProseIndex":
        chunks = build_corpus(data_dir)
        vectors = embed_texts([f"{c.title}\n{c.text}" for c in chunks])
        _CACHE.mkdir(exist_ok=True)
        np.save(_VECS, vectors)
        _META.write_text(json.dumps([c.model_dump() for c in chunks]))
        return cls(chunks, vectors)

    @classmethod
    def load(cls) -> Optional["ProseIndex"]:
        if not (_VECS.exists() and _META.exists()):
            return None
        chunks = [Chunk(**d) for d in json.loads(_META.read_text())]
        return cls(chunks, np.load(_VECS))

    @classmethod
    def get(cls, data_dir: str | Path, rebuild: bool = False) -> "ProseIndex":
        if not rebuild:
            existing = cls.load()
            if existing is not None:
                return existing
        return cls.build(data_dir)

    # ---- search ----
    def search(self, query: str, k: int = 5, alpha: float = 0.7) -> list[dict]:
        qv = embed_query(query)
        cos = self.vectors @ qv  # both unit-normalized
        qkw = _keywords(query)
        results = []
        for i, chunk in enumerate(self.chunks):
            kw = (len(qkw & self._kw[i]) / len(qkw)) if qkw else 0.0
            score = alpha * float(cos[i]) + (1 - alpha) * kw
            results.append((score, i))
        results.sort(reverse=True)
        out = []
        for score, i in results[:k]:
            c = self.chunks[i]
            out.append({
                "source": c.source,
                "title": c.title,
                "score": round(score, 3),
                "text": c.text[:700],
            })
        return out


_SINGLETON: Optional[ProseIndex] = None


def search_prose(query: str, k: int = 5) -> list[dict]:
    """Module-level convenience: lazily load/build the index, then search."""
    global _SINGLETON
    if _SINGLETON is None:
        _SINGLETON = ProseIndex.get(settings.data_dir)
    return _SINGLETON.search(query, k)
