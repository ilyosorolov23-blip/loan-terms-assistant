"""
FastAPI entrypoint.

    uvicorn app.main:app --reload --port 8000

Endpoints:
    GET  /api/documents          -> list of documents the agent can discuss
    POST /api/chat               -> {question, doc_id} -> AgentResult
    GET  /healthz                -> liveness probe
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config
from .agent import ask

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("loan_assistant.api")

app = FastAPI(
    title="Loan Terms Assistant API",
    description="A scoped, secure RAG agent that answers questions about real bank loan documents.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str
    doc_id: str = config.DEFAULT_DOCUMENT


class ChatResponse(BaseModel):
    status: str
    text: str
    citations: list[int] = []
    sources: list[dict] = []
    steps: list[str] = []


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/api/documents")
def list_documents():
    return [
        {
            "id": d.id,
            "bank": d.bank,
            "country": d.country,
            "flag": d.flag,
        }
        for d in config.DOCUMENTS.values()
    ]


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    if req.doc_id not in config.DOCUMENTS:
        raise HTTPException(status_code=404, detail=f"unknown document id: {req.doc_id}")
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty")

    logger.info("doc=%s question=%r", req.doc_id, req.question)
    try:
        result = ask(req.question, req.doc_id)
    except Exception as exc:  # noqa: BLE001 - surface a clean 500 to the client
        logger.exception("agent failed")
        raise HTTPException(status_code=500, detail="the agent failed to process this question") from exc

    return ChatResponse(
        status=result.status,
        text=result.text,
        citations=result.citations,
        sources=result.sources,
        steps=result.steps,
    )


# Serve the static frontend (built as a single page) at /
try:
    app.mount("/", StaticFiles(directory=str(config.BASE_DIR.parent / "frontend"), html=True), name="frontend")
except RuntimeError:
    # frontend folder not present in this checkout — API-only mode
    pass
