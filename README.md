# The Loan Vault — Loan Terms Assistant

A scoped, secure RAG agent that answers questions about **real bank loan
documents** — and refuses everything else. Built from the student guide,
taken one level further: a FastAPI backend, five real public loan/credit
contracts instead of one, and a modern chat UI instead of the default
Gradio widget.

## What's different from the guide

| Guide | This build |
|---|---|
| One hard-coded PDF | 5 real bank documents, switchable in the sidebar, each with its own scope + its own vector collection |
| Gradio `ChatInterface` | FastAPI JSON API + a hand-built HTML/CSS/JS frontend |
| Functions in loose `.py` files | Same 4-step pipeline (`guard → retrieve → answer → verify`), packaged as an installable `app/` module with typed results |
| No visible pipeline | The UI animates the 4 steps live and stamps every answer **verified** or **blocked** |
| No source view | Click a page citation to expand the exact contract excerpt it came from |

The two security ideas from the guide are unchanged and still do all the work:

1. **Scope guard** (`app/guard.py`) — refuses anything that isn't a factual
   question about *this* product's own terms (no advice, no other banks,
   no small talk).
2. **Grounding guard** (`app/verify.py`) — re-checks the draft answer
   against the retrieved clauses and blocks it if it isn't actually
   supported by the text.

## Documents included

All five are real, public, text-based PDFs (not scanned images), already in
`backend/docs/`:

- Standard Chartered Bank (Vietnam) — Personal Loan T&Cs
- CIBC (Canada) — Personal Loan T&Cs
- CIMB Bank (Malaysia) — Personal Loan T&Cs
- National Bank of Uzbekistan — Consumer Loan Agreement
- South Indian Bank — Personal Loan Agreement

Swap or add documents by editing `DOCUMENTS` in `backend/app/config.py` and
dropping the PDF into `backend/docs/`.

## Project structure

```
loan-terms-assistant/
├─ backend/
│  ├─ app/
│  │  ├─ config.py      # settings + the document registry (scope lives here)
│  │  ├─ llm.py          # the ONE place that calls the class proxy (Gemini)
│  │  ├─ ingest.py       # PDF -> chunks -> embeddings -> Qdrant, per document
│  │  ├─ guard.py        # SECURITY 1: scope guard
│  │  ├─ retrieve.py     # vector search over one document's clauses
│  │  ├─ answer.py       # answer strictly from retrieved clauses, cite page
│  │  ├─ verify.py       # SECURITY 2: grounding guard
│  │  ├─ agent.py        # wires the 4 steps together
│  │  └─ main.py         # FastAPI app (REST API + serves the frontend)
│  ├─ docs/               # the 5 real PDFs
│  ├─ data/                # local Qdrant storage (git-ignored)
│  ├─ requirements.txt
│  └─ .env.example
├─ frontend/
│  ├─ index.html          # the chat UI
│  ├─ app.js               # talks to /api/documents and /api/chat
│  └─ styles.css
└─ README.md
```

## Run it

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# paste the key your mentor gave you into .env

# build the vector index for every document (run once, or after editing a PDF)
python -m app.ingest

# start the API + UI
uvicorn app.main:app --reload --port 8000
# open http://127.0.0.1:8000
```

To re-index a single document after replacing its PDF:

```bash
python -m app.ingest scb
```

## API

```
GET  /api/documents            -> [{id, bank, country, flag}, ...]
POST /api/chat  {question, doc_id}
     -> {status: "grounded" | "refused" | "blocked",
         text, citations: [page, ...], sources: [{text, page, score}, ...], steps}
```

## Also included: a zero-setup live demo

`loan_vault_demo.html` (in this folder) is a **standalone** version of the
same UI that runs entirely in the browser — no backend, no API key to
configure. It does its own local TF-IDF retrieval over the same 5 PDFs and
calls Claude directly for the guard/answer/verify steps. Open it straight
in a browser to try the pipeline immediately; use the FastAPI version above
for the actual assignment (Gemini via the class proxy, as required).

## Testing it like a mentor

Pick a document, then try all three behaviours:

- **In scope:** "What is the late-payment penalty?" → answer + page, e.g. (p. 4)
- **Off-topic / advice:** "Should I take this loan?" or "Write me a poem." → refused
- **Not in the document:** ask about something the contract never mentions → "Not stated in the terms."

Golden test: open the PDF yourself, find the real number, and confirm the
agent's answer matches exactly.
