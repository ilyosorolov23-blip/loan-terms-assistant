"""
Read a PDF -> cut into overlapping chunks -> embed each chunk -> store in a
local Qdrant collection. Run once per document (or whenever a PDF changes).

    python -m app.ingest            # ingest every document in config.DOCUMENTS
    python -m app.ingest scb        # ingest just one document by id
"""
from __future__ import annotations

import logging
import sys

from pypdf import PdfReader
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from . import config
from .llm import embed

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("loan_assistant.ingest")


def load_chunks(pdf_path, size=config.CHUNK_SIZE, overlap=config.CHUNK_OVERLAP):
    """Read the PDF and cut each page into small overlapping pieces."""
    reader = PdfReader(str(pdf_path))
    chunks = []
    for page_no, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            continue
        start = 0
        while start < len(text):
            piece = text[start : start + size]
            if len(piece.strip()) > 30:
                chunks.append({"text": piece, "page": page_no})
            start += size - overlap
    return chunks


def ingest_document(doc_id: str) -> int:
    spec = config.DOCUMENTS[doc_id]
    chunks = load_chunks(spec.path)
    logger.info("[%s] %s — loaded %d chunks from %s", doc_id, spec.bank, len(chunks), spec.filename)

    dim = len(embed("dimension probe"))
    client = QdrantClient(path=config.QDRANT_PATH)
    client.recreate_collection(
        collection_name=spec.collection,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
    )

    points = []
    for i, c in enumerate(chunks):
        points.append(
            PointStruct(id=i, vector=embed(c["text"]), payload={"text": c["text"], "page": c["page"]})
        )
    client.upsert(collection_name=spec.collection, points=points)
    logger.info("[%s] stored %d clauses in Qdrant collection '%s'", doc_id, len(points), spec.collection)
    return len(points)


def main():
    targets = sys.argv[1:] or list(config.DOCUMENTS.keys())
    for doc_id in targets:
        if doc_id not in config.DOCUMENTS:
            logger.warning("skipping unknown document id: %s", doc_id)
            continue
        ingest_document(doc_id)
    logger.info("Done. %d document(s) ready.", len(targets))


if __name__ == "__main__":
    main()
