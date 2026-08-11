"""
Central settings for the Loan Terms Assistant.

Everything that can change (proxy URL, model names, which documents are
loaded, how big a chunk is) lives here so the rest of the codebase never
hard-codes it.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "docs"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# --- your API key (from your mentor / class proxy) ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing. Copy .env.example to .env and paste the "
        "key your mentor gave you."
    )

# --- the class proxy: ALL AI calls go through here ---
PROXY_BASE = os.getenv("PROXY_BASE", "https://saidazam-litellm-proxy.hf.space/gemini")

# --- model names (the ONLY ones the proxy allows) ---
CHAT_MODEL = os.getenv("CHAT_MODEL", "gemini-flash-lite")
EMBED_MODEL = os.getenv("EMBED_MODEL", "gemini-embedding")

# --- retrieval ---
CHUNK_SIZE = 900
CHUNK_OVERLAP = 150
TOP_K = 5

# --- server ---
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")


@dataclass(frozen=True)
class DocumentSpec:
    """One loan / credit product the assistant is allowed to discuss."""

    id: str
    bank: str
    country: str
    flag: str
    filename: str
    scope: str = field(default="")

    @property
    def path(self) -> Path:
        return DOCS_DIR / self.filename

    @property
    def collection(self) -> str:
        return f"loan_terms_{self.id}"

    def resolved_scope(self) -> str:
        if self.scope:
            return self.scope
        return (
            f"the terms and conditions of the {self.bank} ({self.country}) "
            "personal loan / credit product: interest rate, fees, repayment "
            "schedule, penalties, eligibility, collateral, and what the "
            "contract does or does not include"
        )


# --- THE documents this assistant is allowed to talk about ---
# Add / remove entries here to change what the agent can discuss.
# Each document gets its OWN scope, its OWN Qdrant collection, and its OWN
# chat history — the agent never mixes clauses from two different banks.
DOCUMENTS: dict[str, DocumentSpec] = {
    d.id: d
    for d in [
        DocumentSpec("scb", "Standard Chartered Bank", "Vietnam", "🇻🇳", "standard_chartered_loan.pdf"),
        DocumentSpec("cibc", "CIBC", "Canada", "🇨🇦", "cibc_personal_loan.pdf"),
        DocumentSpec("cimb", "CIMB Bank", "Malaysia", "🇲🇾", "cimb_personal_loan.pdf"),
        DocumentSpec("nbu", "National Bank of Uzbekistan", "Uzbekistan", "🇺🇿", "nbu_uzbek_consumer_loan.pdf"),
        DocumentSpec("sib", "South Indian Bank", "India", "🇮🇳", "south_indian_bank_loan.pdf"),
    ]
}

DEFAULT_DOCUMENT = "scb"
QDRANT_PATH = str(DATA_DIR / "qdrant_data")
