# LegacyLens — RAG Architecture Document

**Project:** RAG System for Legacy COBOL Codebases
**Codebase:** GnuCOBOL / cobol-rekt-rd + proleap-cobol (432 files, 354,457 LOC)
**Stack:** Python + FastAPI, LangChain, Pinecone, OpenAI, Next.js

---

## 1. Vector Database Selection: Pinecone

**Choice:** Pinecone (managed cloud, free Starter tier)

**Rationale:**
Pinecone was selected for its fully managed infrastructure — no servers to configure, no
DevOps overhead. For a one-week sprint, this was critical. The Python SDK integrates
natively with LangChain, and the free Starter tier (2GB storage, 2M write units) was
sufficient to store 16,406 chunks from the full codebase.

**Tradeoffs considered:**

| Database | Why rejected |
|----------|--------------|
| ChromaDB | No managed hosting; local-only for prototyping |
| Qdrant | Self-hosting adds DevOps complexity |
| pgvector | Requires a full Postgres instance |
| Weaviate | GraphQL API adds learning curve |

**Index configuration:** 1024 dimensions, cosine similarity metric, AWS us-east-1.
Dimensions were set to 1024 to match the Pinecone Starter index default, and
OpenAI text-embedding-3-small was configured to match via the `dimensions` parameter.

---

## 2. Embedding Strategy: OpenAI text-embedding-3-small

**Model:** `text-embedding-3-small` with `dimensions=1024`
**Cost:** $0.02 per 1M tokens

**Rationale:**
This model provides strong semantic understanding of both natural language queries and
code structure. Its support for custom output dimensions allowed us to match the 1024-dim
Pinecone index without quality loss. It is natively supported by LangChain's
`OpenAIEmbeddings` class, minimizing integration complexity.

**Alternatives considered:**
- *Voyage Code 2* — code-optimized embeddings, but adds a second API dependency
and billing account. Kept as an upgrade path if retrieval precision drops below 70%.
- *sentence-transformers (local)* — free, but local inference on 354K LOC would take
hours without a GPU.

**Batching:** Chunks are embedded in batches of 100 to stay within OpenAI rate limits.
Total ingestion: 16,406 chunks uploaded in 7.1 minutes.

---

## 3. Chunking Approach

**Primary strategy: COBOL paragraph-level chunking**

COBOL organizes logic into named PARAGRAPHS and SECTIONS — these are natural
semantic units equivalent to functions in modern languages. The ingestion pipeline uses
a regex pattern to detect paragraph headers (lines matching `PARAGRAPH-NAME.`) and
splits the file at each boundary.

**Fallback strategy: Fixed-size token chunking**

For files that do not follow standard COBOL paragraph structure, a fallback chunker
splits the file into 512-token windows with 50-token overlap to preserve context across
boundaries.

**Metadata attached to every chunk:**
- `file_name` — basename of the source file
- `source` — full file path (used for drill-down)
- `paragraph` — detected paragraph/section name
- `start_line` — first line of the chunk
- `end_line` — last line of the chunk

**Why this matters:** Paragraph-level chunks map directly to what developers think about
when navigating COBOL. A query like "Explain what CALCULATE-INTEREST does" retrieves
the exact paragraph rather than an arbitrary 512-token window that might split the logic.

---

## 4. Retrieval Pipeline

**Query flow:**
```
User natural language query
        ↓
OpenAI text-embedding-3-small (1024 dims)
        ↓
Pinecone similarity_search_with_score (top-3, cosine)
        ↓
Score conversion: (1 - distance) × 100 → percentage
        ↓
Context assembly: chunks + file/line metadata headers
        ↓
GPT-4o (COBOL expert system prompt + assembled context)
        ↓
Answer + source citations with confidence scores
```

**Top-k:** 3 chunks per query (reduced from 5 to improve latency)

**Re-ranking:** Not implemented in MVP. Cohere Rerank API identified as next upgrade
to improve result ordering for ambiguous queries.

**Context assembly:** Retrieved chunks are concatenated with file path and line number
headers before being passed to GPT-4o, ensuring every answer can cite exact locations.

**Confidence scores:** Cosine distance is converted to a 0–100% similarity score and
displayed as color-coded badges (green ≥80%, yellow ≥50%, red <50%).

---

## 5. Failure Modes

**What doesn't work well:**

1. **Queries about non-existent identifiers** — Queries like "What functions modify
CUSTOMER-RECORD?" return no relevant results because this identifier does not
exist in the indexed codebases. The LLM correctly reports it cannot find the context,
but the UX could be improved with a clearer "not found" message.

2. **Query latency variability** — Some queries exceed the 3-second target (observed
range: 662ms–4,842ms). Latency spikes correlate with longer GPT-4o responses.
Mitigation: reduced top-k to 3 and capped max_tokens.

3. **Full file view in production** — The `/file` endpoint reads files from the local
`codebase/` directory. Since the codebase is gitignored and not bundled with the
Railway deployment, this feature only works locally.

4. **Ingestion throughput** — Full ingestion of 354,457 LOC took 7.1 minutes, slightly
above the 5-minute target. Parallelizing the embedding API calls is the primary
optimization path.

5. **Paragraph detection edge cases** — Some COBOL files use non-standard formatting
or continuation lines that the regex parser misses, falling back to fixed-size chunking.

---

## 6. Performance Results

| Metric | Target | Actual |
|--------|--------|--------|
| Query latency | <3,000ms | 662ms–4,447ms (avg ~3,000ms) |
| Retrieval precision | >70% relevant in top-3 | ~75% based on manual spot checks |
| Codebase coverage | 100% of files | 432/432 files indexed |
| Ingestion throughput | 10K LOC in <5 min | 354K LOC in 7.1 min |
| Answer accuracy | Correct file/line refs | Verified on 4 of 6 test queries |

**Example results from live system:**

- *"Find all file I/O operations"* → Returns `nist85.cbl`, `ObsoleteKeywords.cbl` with
exact line ranges for OPEN EXTEND, OPEN INPUT, OPEN I-O operations. Latency: 4,107ms.

- *"Show me error handling patterns"* → Returns 10 relevant chunks across multiple files
with pattern matches. Latency: 662ms.

- *"What are the dependencies of MODULE-X?"* → Returns 10 chunks with 16 call
relationships extracted. Latency: 4,842ms.
