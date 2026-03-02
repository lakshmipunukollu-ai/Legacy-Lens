# Legacy Lens

A RAG-powered web app that makes the GnuCOBOL open source codebase queryable via natural language. Ask questions like "What does the CALCULATE-INTEREST paragraph do?" and get accurate answers with file paths and line numbers.

## Tech Stack

- **Vector DB:** Pinecone (free tier)
- **Embeddings:** OpenAI text-embedding-3-small
- **LLM:** GPT-4o
- **Framework:** LangChain (Python)
- **Backend:** Python + FastAPI
- **Frontend:** React + Next.js
- **Deployment:** Railway (backend) + Vercel (frontend)

## Setup

The codebase is cloned from `OCamlPro/gnucobol` (GitHub mirror of GnuCOBOL).

```bash
cd backend
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

Copy `backend/.env.example` to `backend/.env` and add your API keys.

**Pinecone:** Create index (e.g. `legacylens-vectors`) with **dimensions=1024**, metric=cosine, **no** integrated embedding model (bring your own vectors).

**If you get 401 Invalid API Key:** Add your index host to `backend/.env` so the app skips control-plane auth. In [Pinecone Console](https://app.pinecone.io/) → Indexes → your index → copy the **Host** value. Then add:
```bash
PINECONE_INDEX_HOST=your-index-host.svc.region.pinecone.io
```

## Running Locally

Run these from the **legacylens** folder (or use `legacylens/` in the path):

1. **Backend:** `cd legacylens/backend && source venv/bin/activate && uvicorn main:app --reload --port 8000`
2. **Frontend:** `cd legacylens/frontend && npm run dev`
3. **Ingest:** `cd legacylens/backend && source venv/bin/activate && python ingest.py` (run once)

## Deploy (Phase 6)

See **[DEPLOY.md](DEPLOY.md)** for Railway (backend) and Vercel (frontend) steps.

## API — Code Understanding (Phase 7)

- `POST /query` — RAG Q&A
- `POST /dependencies` — PERFORM/call graph
- `POST /document` — Generate technical docs for a paragraph/file
- `POST /patterns` — Find file I/O (OPEN, READ, WRITE) patterns
