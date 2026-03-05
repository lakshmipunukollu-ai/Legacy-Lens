# LegacyLens

> RAG-powered natural language search for legacy COBOL codebases

## 🚀 Live Demo

- **Frontend:** https://legacy-lens-nine.vercel.app
- **Backend API:** https://legacy-lens-production-5e14.up.railway.app

## 📹 Demo Video

[Watch the demo on Loom](https://www.loom.com/share/f037e325963f4a988fd31a5387dceba8)

## Architecture

LegacyLens uses a Retrieval-Augmented Generation (RAG) pipeline to make legacy COBOL code queryable via natural language.

### Full Pipeline

```
User Query
    ↓
OpenAI text-embedding-3-small (1024 dims)
    ↓
Pinecone Similarity Search (top-1 chunk, cosine)
    ↓
Context Assembly (chunks + file/line metadata)
    ↓
GPT-4o-mini (COBOL expert system prompt)
    ↓
Answer + Source Citations
```

### Ingestion Pipeline

1. Recursively scan codebase for .cob, .cbl, .cpy files
2. Normalize encoding to UTF-8, strip non-printable characters
3. Split by COBOL PARAGRAPH boundaries (regex pattern matching)
4. Fallback: fixed-size chunks (512 tokens, 50-token overlap)
5. Attach metadata: file_name, source path, paragraph name, start_line, end_line
6. Generate embeddings via OpenAI text-embedding-3-small (1024 dims)
7. Upload to Pinecone with metadata

### Tech Stack

| Layer | Technology |
|-------|------------|
| Vector DB | Pinecone (cosine, 1024 dims) |
| Embeddings | OpenAI text-embedding-3-small |
| LLM | GPT-4o-mini |
| Framework | LangChain |
| Backend | Python + FastAPI |
| Frontend | Next.js + Tailwind CSS |
| Deployment | Railway (backend) + Vercel (frontend) |

---

## Tech Stack (summary)

- **Vector DB:** Pinecone (free tier)
- **Embeddings:** OpenAI text-embedding-3-small
- **LLM:** GPT-4o-mini
- **Framework:** LangChain (Python)
- **Backend:** Python + FastAPI
- **Frontend:** React + Next.js
- **Deployment:** Railway (backend) + Vercel (frontend)

## Setup

The codebase combines COBOL from `mechanical-orchard/cobol-rekt-rd` and `uwol/proleap-cobol`. Clone both into `codebase/`:

```bash
mkdir -p codebase
git clone --depth 1 https://github.com/mechanical-orchard/cobol-rekt-rd.git codebase/cobol-rekt
git clone --depth 1 https://github.com/uwol/proleap-cobol.git codebase/proleap-cobol
```

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

## API — Code Understanding

- `POST /query` — RAG Q&A
- `POST /dependencies` — PERFORM/call graph
- `POST /document` — Generate technical docs for a paragraph/file
- `POST /patterns` — Find file I/O (OPEN, READ, WRITE) patterns
- `GET /file?path=...` — Full file content for drill-down
