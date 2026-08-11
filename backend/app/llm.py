"""
gem.py, but promoted to a small module: the ONLY place in the codebase that
talks to the class proxy. Every other module imports `chat()` and `embed()`
from here — swap providers once, and the whole app follows.
"""
from __future__ import annotations

import logging
import os
import re

from google import genai

from . import config

logger = logging.getLogger("loan_assistant.llm")

_client = genai.Client(
    api_key=config.GEMINI_API_KEY,
    http_options={"base_url": config.PROXY_BASE},
)


def chat(prompt: str) -> str:
    """Send a prompt to the thinking model, return its text (never raises on empty)."""
    # Local fallback mode: lightweight, deterministic behavior for testing
    if os.getenv("LOCAL_FALLBACK", "0") == "1":
        p = prompt.strip()
        # Guard prompt path: return ALLOW or REFUSE based on simple heuristics
        if "User question:" in p and "Answer (ALLOW or REFUSE):" in p:
            # extract the user question
            try:
                q = p.split("User question:", 1)[1].split("Answer", 1)[0].strip()
            except Exception:
                q = p
            ql = q.lower()
            allow_keywords = [
                "rate",
                "interest",
                "fee",
                "penalty",
                "late",
                "payment",
                "repay",
                "eligib",
                "collateral",
                "term",
            ]
            if any(k in ql for k in allow_keywords):
                return "ALLOW"
            return "REFUSE"

        # Answer prompt path: prompt contains Context: ... Question: ...
        if "Context:" in p and "Question:" in p:
            try:
                ctx = p.split("Context:", 1)[1].split("Question:", 1)[0].strip()
                q = p.split("Question:", 1)[1].strip()
            except Exception:
                return "Not stated in the terms."

            # parse context blocks like "[p. X] text"
            blocks = []
            for part in ctx.split("\n\n"):
                part = part.strip()
                if not part:
                    continue
                m = re.match(r"\[p\.\s*(\d+)\]\s*(.*)$", part, flags=re.S)
                if m:
                    page = int(m.group(1))
                    text = m.group(2).strip()
                else:
                    # fallback: try to recover a page indicator
                    page = None
                    text = part
                blocks.append({"page": page, "text": text})

            # simple keyword overlap scoring
            qtokens = re.findall(r"\w+", q.lower())
            best = None
            best_score = 0
            for b in blocks:
                words = re.findall(r"\w+", b["text"].lower())
                score = sum(1 for t in qtokens if t in words)
                if score > best_score:
                    best_score = score
                    best = b

            if best and best_score > 0:
                pg = f"(p. {best['page']})" if best.get("page") else ""
                # return a concise extractive answer
                snippet = best["text"]
                # ensure the answer includes a page citation as required
                return f"{snippet} {pg}".strip()

            return "Not stated in the terms."

        # Verify prompt path: check whether ANSWER is supported by CONTEXT
        if "Check if the ANSWER is fully supported" in p and "Verdict:" in p:
            # extract context and answer
            try:
                ctx = p.split("CONTEXT:", 1)[1].split("ANSWER:", 1)[0].strip()
                ans = p.split("ANSWER:", 1)[1].split("Verdict:", 1)[0].strip()
            except Exception:
                return "NOT_GROUNDED"

            if ans.strip().startswith("Not stated in the terms."):
                return "GROUNDED"

            # simple substring check: if any context block appears in the answer, ground it
            ctx_blocks = [b.strip().lower() for b in ctx.split("\n\n") if b.strip()]
            ans_l = ans.lower()
            for b in ctx_blocks:
                if b in ans_l or ans_l in b:
                    return "GROUNDED"
            # fallback: check token overlap
            import re as _re
            ans_tokens = set(_re.findall(r"\w+", ans_l))
            for b in ctx_blocks:
                b_tokens = set(_re.findall(r"\w+", b))
                if not ans_tokens:
                    continue
                overlap = len(ans_tokens & b_tokens) / max(1, len(ans_tokens))
                if overlap > 0.3:
                    return "GROUNDED"
            return "NOT_GROUNDED"

        # Generic fallback: echo a short reply
        return (p[:400] + "...") if p else ""

    # Normal remote call
    resp = _client.models.generate_content(model=config.CHAT_MODEL, contents=prompt)
    return (resp.text or "").strip()


def embed(text: str) -> list[float]:
    """Turn text into a vector using the embedding model."""
    # Local deterministic embedding fallback to avoid remote calls during testing
    if os.getenv("LOCAL_FALLBACK", "0") == "1":
        # fixed embedding dimension (choose a commonly used size)
        dim = 1536
        import hashlib

        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        seed = int(h, 16)
        rnd = __import__("random").Random(seed)
        return [rnd.uniform(-1.0, 1.0) for _ in range(dim)]

    resp = _client.models.embed_content(model=config.EMBED_MODEL, contents=text)
    return resp.embeddings[0].values
