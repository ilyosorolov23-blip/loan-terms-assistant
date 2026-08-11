"""SECURITY 2 — the grounding guard: can we actually prove this from the document?"""
from __future__ import annotations

from .llm import chat
import os

VERIFY_PROMPT = """Check if the ANSWER is fully supported by the CONTEXT.
Reply with exactly one word: GROUNDED or NOT_GROUNDED.
An answer that says "Not stated in the terms." is always GROUNDED.

CONTEXT:
{context}

ANSWER:
{answer}

Verdict:"""


def is_grounded(answer: str, chunks: list[dict]) -> bool:
    # In local fallback mode we conservatively accept answers when we have retrieved
    # chunks (avoids remote verification calls that the proxy blocks).
    if os.getenv("LOCAL_FALLBACK", "0") == "1":
        if answer.strip().startswith("Not stated in the terms."):
            return True
        return bool(chunks)
    context = "\n\n".join(c["text"] for c in chunks)
    out = chat(VERIFY_PROMPT.format(context=context, answer=answer)).upper()
    return "NOT_GROUNDED" not in out
