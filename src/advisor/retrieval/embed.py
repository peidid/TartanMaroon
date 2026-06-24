"""Thin OpenAI embeddings wrapper (batched, L2-normalized)."""

from __future__ import annotations

import numpy as np
from openai import OpenAI

from ..config import settings

_BATCH = 128


def embed_texts(texts: list[str], model: str | None = None) -> np.ndarray:
    """Return an (n, dim) float32 array of unit-normalized embeddings."""
    client = OpenAI(api_key=settings.openai_api_key)
    model = model or settings.embed_model
    vecs: list[list[float]] = []
    for i in range(0, len(texts), _BATCH):
        batch = [t.replace("\n", " ")[:8000] for t in texts[i:i + _BATCH]]
        resp = client.embeddings.create(model=model, input=batch)
        vecs.extend(d.embedding for d in resp.data)
    arr = np.asarray(vecs, dtype=np.float32)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return arr / norms


def embed_query(text: str, model: str | None = None) -> np.ndarray:
    return embed_texts([text], model)[0]
