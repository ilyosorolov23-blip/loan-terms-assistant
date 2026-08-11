"""Find the clauses (from ONE document's Qdrant collection) closest to a question."""
from __future__ import annotations

from qdrant_client import QdrantClient

from . import config
from .config import DocumentSpec
from .llm import embed

_client = QdrantClient(path=config.QDRANT_PATH)


def search(question: str, doc: DocumentSpec, k: int = config.TOP_K):
    vec = embed(question)
    hits = _client.search(collection_name=doc.collection, query_vector=vec, limit=k)
    return [{"text": h.payload["text"], "page": h.payload["page"], "score": h.score} for h in hits]
