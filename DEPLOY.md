# LegacyLens Deployment

## Phase 6 — Deploy

### 1. Backend → Railway

1. Push the `legacylens` repo to GitHub (if not already).
2. Go to [Railway](https://railway.app/) → **New Project** → **Deploy from GitHub**.
3. Select your repo. Set **Root Directory** to `legacylens/backend` (or the folder that contains `main.py` and `requirements.txt`).
4. Add **Environment Variables** (Settings → Variables):
   - `OPENAI_API_KEY`
   - `PINECONE_API_KEY`
   - `PINECONE_INDEX_NAME` (e.g. `legacylens-vectors`)
   - `PINECONE_INDEX_HOST` (your index host, e.g. `legacylens-vectors-xxxx.svc.aped-4627-b74a.pinecone.io`)
5. Set **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Deploy. Copy the public URL (e.g. `https://your-app.up.railway.app`).

### 2. Frontend → Vercel

1. Go to [Vercel](https://vercel.com/) → **Add New** → **Project** → Import your GitHub repo.
2. Set **Root Directory** to `legacylens/frontend`.
3. Add **Environment Variable**: `NEXT_PUBLIC_API_URL` = your Railway backend URL (e.g. `https://your-app.up.railway.app`).
4. Deploy. Your app will be at `https://your-project.vercel.app`.

### 3. Verify

- Backend: `https://your-railway-url.up.railway.app/health` → `{"status":"ok"}`
- Frontend: Open the Vercel URL and run a query.

---

## Phase 7 — API Endpoints (Code Understanding)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/query` | POST | RAG Q&A (body: `{"question": "..."}`) |
| `/dependencies` | POST | PERFORM/call graph (body: `{"question": "MODULE-X"}` or `{}` for all) |
| `/document` | POST | Generate docs for a paragraph/file (body: `{"paragraph": "NAME"}` or `{"file_name": "x.cob"}`) |
| `/patterns` | POST | Find file I/O patterns (body: `{"keyword": "OPEN READ WRITE"}`) |
| `/health` | GET | Health check |
