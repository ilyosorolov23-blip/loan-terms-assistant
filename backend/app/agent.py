"""Wires guard -> retrieve -> answer -> verify into one call, per document."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import config
from .answer import write_answer
from .guard import is_in_scope
from .retrieve import search
from .verify import is_grounded

REFUSAL = "I can only answer questions about this loan product's terms and conditions."
UNCONFIRMED = "I can't confirm this from the document."

_PAGE_RE = re.compile(r"p\.\s?(\d+)")


@dataclass
class AgentResult:
    status: str  # "refused" | "blocked" | "grounded"
    text: str
    citations: list[int] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)


def ask(question: str, doc_id: str) -> AgentResult:
    if doc_id not in config.DOCUMENTS:
        raise ValueError(f"unknown document id: {doc_id}")
    doc = config.DOCUMENTS[doc_id]
    steps = []

    # STEP 1 - INPUT GUARD (security): is the question in scope?
    steps.append("scope_guard")
    if not is_in_scope(question, doc):
        return AgentResult(status="refused", text=REFUSAL, steps=steps)

    # STEP 2 - retrieve the real clauses from the PDF
    steps.append("retrieve")
    chunks = search(question, doc)

    # STEP 3 - answer using ONLY those clauses
    steps.append("answer")
    draft = write_answer(question, chunks)

    # STEP 4 - OUTPUT GUARD (security): is the answer backed by the PDF?
    steps.append("grounding_guard")
    if not is_grounded(draft, chunks):
        return AgentResult(status="blocked", text=UNCONFIRMED, sources=chunks, steps=steps)

    pages = [int(p) for p in _PAGE_RE.findall(draft)]
    if not pages:
        pages = sorted({c["page"] for c in chunks[:2]})

    return AgentResult(status="grounded", text=draft, citations=pages, sources=chunks, steps=steps)


if __name__ == "__main__":
    tests = [
        ("What is the late payment penalty?", config.DEFAULT_DOCUMENT),  # in scope  -> answer + page
        ("Write me a poem about the moon.", config.DEFAULT_DOCUMENT),  # off topic -> refused
        ("What is the interest rate on a car?", config.DEFAULT_DOCUMENT),  # maybe not in this doc
    ]
    for q, doc_id in tests:
        print(">", q)
        result = ask(q, doc_id)
        print(f"[{result.status}]", result.text, "\n")
