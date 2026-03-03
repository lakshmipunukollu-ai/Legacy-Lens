# LegacyLens — Pre-Search Document

**Project:** RAG System for Legacy Enterprise Codebases | **Codebase:** GnuCOBOL

## Phase 1: Define Your Constraints

**1. Scale & Load Profile**

GnuCOBOL contains ~150,000+ lines of code across 200+ files. Expected query volume: ~50–200/day during development, 100–500/day per user in production. Batch ingestion on first run, incremental updates after. Latency target: under 3 seconds end-to-end.

**2. Budget & Cost Ceiling**

Pinecone free tier = $0 during dev. OpenAI text-embedding-3-small at $0.02/1M tokens — indexing full codebase estimated at ~3–5M tokens (~$0.06–$0.10 one-time). GPT-4o answer generation ~$0.01–$0.03 per query. Decision: use text-embedding-3-small to save 50%+ on cost vs large model.

**3. Time to Ship**

MVP (24 hours): ingestion + Pinecone storage + semantic search + web interface. Must-haves: chunking, embeddings, retrieval, answer generation, deployed interface. LangChain chosen for speed — best tutorials and AI agent support.

**4. Data Sensitivity**

GnuCOBOL is GNU GPL open source — fully safe to send to external APIs. No data residency concerns.

**5. Team & Skill Constraints**

Limited vector DB experience — Pinecone managed service removes infrastructure burden. Using AI coding agents (Cursor Pro / Claude) throughout. No prior COBOL experience — relying on syntax-aware chunking and LLM understanding.

## Phase 2: Architecture Discovery

**6. Vector Database: Pinecone**

Fully managed, free tier, Python SDK integrates natively with LangChain. Alternatives considered: ChromaDB (no production scaling), Qdrant (self-hosting too complex for solo sprint), pgvector (requires full Postgres setup). Decision: Pinecone wins on speed-to-ship.

**7. Embedding Strategy: OpenAI text-embedding-3-small**

1024 dimensions (matched to Pinecone index), strong quality, native LangChain support, $0.02/1M tokens. Alternatives: Voyage Code 2 (adds API dependency), sentence-transformers (too slow on 150K LOC). Upgrade path: Voyage Code 2 if precision falls below 70%.

**8. Chunking Approach**

Primary: COBOL paragraph-level chunking — COBOL organizes logic into named PARAGRAPHS and SECTIONS. Fallback: fixed-size + overlap (512 tokens, 50-token overlap). Metadata per chunk: file path, line numbers, paragraph name, COBOL division.

**9. Retrieval Pipeline**

Top-5 results per query. Context assembly: chunks with file/line headers passed to LLM. Post-MVP: Cohere Rerank for result reordering. Ambiguous queries: MultiQueryRetriever generates 2–3 variants.

**10. Answer Generation**

LLM: GPT-4o. System prompt establishes COBOL expert role. Every answer cites specific file paths and line numbers. Streaming responses for better UX.

**11. Framework: LangChain**

Largest ecosystem, direct Pinecone + OpenAI integrations, covers full pipeline. Alternatives: LlamaIndex (less flexible for custom chunking), custom (too slow for 24-hour MVP).

## Phase 3: Post-Stack Refinement

**12. Failure Modes**

No results found → clear fallback message + log query. Ambiguous queries → query expansion. Encoding issues → normalize to UTF-8. Rate limiting → exponential backoff on all API calls.

**13. Evaluation Strategy**

Manually evaluate top-5 results for 10–15 representative queries, targeting >70% relevant. Build 10–15 hand-labeled query/answer pairs as ground truth.

**14. Performance Optimization**

Cache embeddings locally during development. Pinecone p1 pod for lowest latency. Query preprocessing: normalize casing, strip punctuation, expand COBOL abbreviations.

**15. Observability**

Log every query, chunk IDs, latency, and API cost. Key metrics: p50/p95 latency, retrieval precision, cost per query.

**16. Deployment & DevOps**

Vercel (frontend) + Railway (backend). All API keys in .env — never committed to GitHub. Re-run ingestion pipeline on any new or changed files.

## Summary Table

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Codebase | GnuCOBOL | Open source, 150K+ LOC, well-structured |
| Vector DB | Pinecone | Managed, free tier, fastest setup |
| Embeddings | OpenAI text-embedding-3-small | Cost-effective, 1024 dims |
| Chunking | COBOL paragraph-level + fallback | Natural COBOL boundaries |
| LLM | GPT-4o | Best code understanding |
| Framework | LangChain | Fastest complete pipeline |
| Backend | Python / FastAPI | LangChain native |
| Frontend | React / Next.js | Clean query interface |
| Deployment | Vercel + Railway | Simple, free tiers available |
