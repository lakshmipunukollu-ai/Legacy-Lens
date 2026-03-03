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
- **Model:** GPT-4o at $5.00/1M input tokens, $15.00/1M output tokens
- **Estimated development queries:** ~200 test queries
- **Average tokens per query:** ~2,000 input (context + question), ~300 output
- **Total LLM cost:** ~$2.09
  - Input: 200 × 2,000 = 400K tokens × $5/1M = $2.00
  - Output: 200 × 300 = 60K tokens × $15/1M = $0.90
  - Subtotal: ~$2.09

### Vector Database
- **Pinecone Starter tier:** $0.00 (free)
- **Storage used:** ~16,406 chunks × 1024 dims = well within 2GB free tier

### Deployment
- **Railway:** Free Starter tier — $0.00
- **Vercel:** Free Hobby tier — $0.00

### Total Development Spend
| Category | Cost |
|----------|------|
| Embeddings (3 ingestion runs) | ~$0.33 |
| GPT-4o (200 test queries) | ~$2.09 |
| Pinecone | $0.00 |
| Railway | $0.00 |
| Vercel | $0.00 |
| **Total** | **~$2.42** |

---

## Production Cost Projections

### Assumptions
- Each user sends **5 queries per day**
- Each query: ~2,000 input tokens, ~300 output tokens (GPT-4o)
- Embedding queries: ~100 tokens each (OpenAI text-embedding-3-small)
- Codebase re-ingestion: once per month (~5.5M tokens)
- 30 days per month

### Per-Query Cost Breakdown
| Component | Cost per query |
|-----------|----------------|
| Query embedding (100 tokens) | $0.000002 |
| GPT-4o input (2,000 tokens) | $0.010000 |
| GPT-4o output (300 tokens) | $0.004500 |
| **Total per query** | **~$0.0145** |

### Monthly Cost by Scale

| Scale | Queries/month | LLM Cost | Embedding Cost | Pinecone | Total/month |
|-------|---------------|----------|----------------|----------|-------------|
| **100 users** | 15,000 | $217.50 | $0.30 | $0 (free) | **~$218** |
| **1,000 users** | 150,000 | $2,175 | $3.00 | $70 (Starter) | **~$2,248** |
| **10,000 users** | 1,500,000 | $21,750 | $30.00 | $700 (Standard) | **~$22,480** |
| **100,000 users** | 15,000,000 | $217,500 | $300.00 | $4,000 (Enterprise) | **~$221,800** |

### Key Cost Observations

**GPT-4o dominates costs at every scale** — it accounts for 97%+ of total spend.
The primary cost optimization lever is reducing tokens per query:
- Reducing top-k from 5 to 3 cuts context by ~40%, saving ~$0.006/query
- Switching to GPT-4o-mini ($0.15/1M input, $0.60/1M output) would reduce LLM
costs by ~95%, bringing 100-user monthly cost from ~$218 to ~$15

**Embedding costs are negligible** — even at 100,000 users, embedding costs are
only ~$300/month, less than 0.2% of total spend.

**Pinecone scales linearly** — free tier handles up to ~1,000 users comfortably.
Above that, dedicated pod pricing applies.

### Cost Optimization Roadmap
1. **Switch to GPT-4o-mini** for simple queries — saves ~95% on LLM costs
2. **Cache frequent queries** — top 20% of queries likely repeat; Redis cache
   would eliminate LLM calls for cached results
3. **Reduce max_tokens** — cap responses at 300 tokens for factual queries
4. **Batch embedding** — embed new code additions in bulk rather than one-by-one
