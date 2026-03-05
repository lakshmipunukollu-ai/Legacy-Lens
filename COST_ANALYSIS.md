# LegacyLens — AI Cost Analysis

**Project:** RAG System for Legacy COBOL Codebases
**Date:** March 2026

---

## Development & Testing Costs (Actual)

### Embedding API Costs
- **Model:** OpenAI text-embedding-3-small at $0.02 per 1M tokens
- **Codebase size:** 354,457 LOC across 432 files
- **Estimated tokens embedded:** ~5.5M tokens (avg 13 tokens/line × 354K lines + overhead)
- **Ingestion runs:** ~3 full re-ingestions during development
- **Total embedding cost:** ~$0.33 (5.5M tokens × 3 runs × $0.02/1M)

### LLM API Costs (Answer Generation)
- **Model:** GPT-4o-mini at $0.15/1M input tokens, $0.60/1M output tokens
- **Estimated development queries:** ~200 test queries
- **Average tokens per query:** ~2,000 input (context + question), ~300 output
- **Total LLM cost:** ~$0.10
  - Input: 200 × 2,000 = 400K tokens × $0.15/1M = $0.06
  - Output: 200 × 300 = 60K tokens × $0.60/1M = $0.04
  - Subtotal: ~$0.10

### Vector Database
- **Pinecone Starter tier:** $0.00 (free)
- **Storage used:** ~16,406 chunks × 1024 dims = well within 2GB free tier

### Deployment
- **Railway:** Hobby plan — $5.00/month (upgraded to eliminate cold starts)
- **Vercel:** Free Hobby tier — $0.00

### Total Development Spend
| Category | Cost |
|----------|------|
| Embeddings (3 ingestion runs) | ~$0.33 |
| GPT-4o-mini (200 test queries) | ~$0.10 |
| Pinecone | $0.00 |
| Railway | $5.00 |
| Vercel | $0.00 |
| **Total** | **~$5.43** |

---

## Production Cost Projections

### Assumptions
- Each user sends **5 queries per day**
- Each query: ~2,000 input tokens, ~300 output tokens (GPT-4o-mini)
- Embedding queries: ~100 tokens each (OpenAI text-embedding-3-small)
- Codebase re-ingestion: once per month (~5.5M tokens)
- 30 days per month

### Per-Query Cost Breakdown
| Component | Cost per query |
|-----------|----------------|
| Query embedding (100 tokens) | $0.000002 |
| GPT-4o-mini input (2,000 tokens) | $0.000300 |
| GPT-4o-mini output (300 tokens) | $0.000180 |
| **Total per query** | **~$0.000482** |

### Monthly Cost by Scale

| Scale | Queries/month | LLM Cost | Embedding Cost | Pinecone | Total/month |
|-------|---------------|----------|----------------|----------|-------------|
| **100 users** | 15,000 | $7.23 | $0.30 | $0 (free) | **~$8** |
| **1,000 users** | 150,000 | $72.30 | $3.00 | $70 (Starter) | **~$145** |
| **10,000 users** | 1,500,000 | $723 | $30.00 | $700 (Standard) | **~$1,453** |
| **100,000 users** | 15,000,000 | $7,230 | $300.00 | $4,000 (Enterprise) | **~$11,530** |

### Key Cost Observations

**GPT-4o-mini is already the cost-optimized choice** — at 100 users, monthly cost is ~$8.
The primary remaining optimization is caching frequent queries with Redis — top 20% of
queries likely repeat; Redis cache would eliminate LLM calls for cached results.

**Embedding costs are negligible** — even at 100,000 users, embedding costs are
only ~$300/month, less than 3% of total spend.

**Pinecone scales linearly** — free tier handles up to ~1,000 users comfortably.
Above that, dedicated pod pricing applies.

### Cost Optimization Roadmap
1. **Cache frequent queries** — top 20% of queries likely repeat; Redis cache
   would eliminate LLM calls for cached results
2. **Reduce max_tokens** — cap responses at 300 tokens for factual queries
3. **Batch embedding** — embed new code additions in bulk rather than one-by-one
