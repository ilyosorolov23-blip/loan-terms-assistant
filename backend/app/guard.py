"""SECURITY 1 — the scope guard: is this question even our job?"""
from __future__ import annotations

from .config import DocumentSpec
from .llm import chat

GUARD_PROMPT = """You are a strict topic gate for a bank Loan-Terms assistant.
The assistant may ONLY answer questions about: {scope}.

Decide if the user's question is INSIDE that topic.
Reply with exactly one word: ALLOW or REFUSE.

Rules:
- Advice or opinions ("should I take this loan?", "is this a good deal?") -> REFUSE.
- General knowledge, jokes, coding, other companies, other banks -> REFUSE.
- Only factual questions about THIS product's own terms -> ALLOW.

User question: {q}
Answer (ALLOW or REFUSE):"""


def is_in_scope(question: str, doc: DocumentSpec) -> bool:
    out = chat(GUARD_PROMPT.format(scope=doc.resolved_scope(), q=question)).upper()
    return out.startswith("ALLOW")
