# LegacyLens Test Results

**Date:** Wednesday Mar 4, 2025  
**Backend:** https://legacy-lens-production-5e14.up.railway.app  
**Frontend:** https://legacy-lens-nine.vercel.app

**Last run:** Post latency fix (max_tokens=200, CONTEXT_MAX_TOKENS=1500, SNIPPET_MAX_CHARS=80)

## Test 1 — Golden Set Evaluation

| ID | Status | Latency | Keyword Score | Sources | Latency Pass | Confidence | File/Line Refs |
|----|--------|---------|---------------|---------|--------------|------------|----------------|
| Q1 | FAIL | 3305ms | 80% | 2 | ✗ | ✓ | ✓ |
| Q2 | FAIL | 1740ms | 0% | 2 | ✓ | ✓ | ✓ |
| Q3 | FAIL | 1414ms | 0% | 2 | ✓ | ✓ | ✓ |
| Q4 | FAIL | 4242ms | 100% | 2 | ✗ | ✓ | ✓ |
| Q5 | PASS | 2292ms | 50% | 3 | ✓ | ✓ | ✓ |
| Q6 | PASS | 758ms | 50% | 2 | ✓ | ✓ | ✓ |
| Q7 | PASS | 2845ms | 33% | 2 | ✓ | ✓ | ✓ |
| Q8 | FAIL | 3595ms | 75% | 2 | ✗ | ✓ | ✓ |
| Q9 | PASS | 6486ms | 100% | 0 | ✓ | ✓ | ✓ |
| Q10 | FAIL | 3403ms | 75% | 2 | ✗ | ✓ | ✓ |

**Overall: 4/10 passed**

*Note: Golden set latency varies by run. Q1, Q4, Q8, Q10 occasionally exceed 3000ms. Latency regression test (3-run average) passes.*

## Test 2 — Retrieval Precision

| ID | Description | Retrieved | Relevant | Precision |
|----|--------------|-----------|----------|-----------|
| P1 | Main entry point query | 2 | 2 | 100% |
| P2 | File I/O query | 2 | 1 | 50% |
| P3 | Error handling query | 2 | 0 | 0% |

**Overall precision: 50% (target: >70%)**

## Test 3 — Latency Regression

| Endpoint | Avg (ms) | Min (ms) | Max (ms) | Target 3000ms |
|----------|----------|----------|----------|---------------|
| GET /health | 282 | 209 | 358 | ✓ PASS |
| GET /stats | 525 | 466 | 593 | ✓ PASS |
| GET /health-dashboard | 528 | 466 | 582 | ✓ PASS |
| POST /query | 2658 | 2231 | 3038 | ✓ PASS |
| POST /dependencies | 2834 | 2350 | 3433 | ✓ PASS |
| POST /patterns | 744 | 688 | 783 | ✓ PASS |
| POST /document | 2873 | 2454 | 3090 | ✓ PASS |
| POST /business-logic | 2762 | 2626 | 2997 | ✓ PASS |
| POST /clear-history | 217 | 211 | 222 | ✓ PASS |

**All endpoints under 3,000ms: Yes**

## Test 4 — Response Shape

| Endpoint | Status |
|----------|--------|
| GET /health | ✅ PASS |
| GET /stats | ✅ PASS |
| GET /health-dashboard | ✅ PASS |
| POST /query | ✅ PASS |
| POST /dependencies | ✅ PASS |
| POST /patterns | ✅ PASS |
| POST /document | ✅ PASS |
| POST /business-logic | ✅ PASS |
| POST /explain-snippet | ✅ PASS |
| POST /clear-history | ✅ PASS |

**All shapes correct: Yes (10/10)**

## Test 5 — Multi-turn Conversation

| Turn | Question | Latency | Answer Received |
|------|----------|---------|-----------------|
| 1 | Where is the main entry point of this program? | 2085ms | ✓ |
| 2 | What does that section do in detail? | 1067ms | ✗ |
| 3 | What other paragraphs are near it? | 1726ms | ✓ |
| 4 | What data does it use? | 4410ms | ✓ |

**All turns answered: 3/4** (Turn 2 returns "I couldn't find" — short answer)

*Note: Client-side history persists. Turn 2 failure is retrieval quality, not history.*

## Summary

| Test | Result |
|------|--------|
| Golden Set | 4/10 |
| Retrieval Precision | 50% |
| Latency Regression | Pass |
| Response Shape | Pass |
| Multi-turn | 3/4 |
