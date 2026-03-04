# LegacyLens Test Results

**Date:** Wednesday Mar 4, 2025  
**Backend:** https://legacy-lens-production-5e14.up.railway.app  
**Frontend:** https://legacy-lens-nine.vercel.app

## Test 1 — Golden Set Evaluation

| ID | Status | Latency | Keyword Score | Sources | Latency Pass | Confidence | File/Line Refs |
|----|--------|---------|---------------|---------|--------------|------------|----------------|
| Q1 | PASS | 2363ms | 40% | 1 | ✓ | ✓ | ✓ |
| Q2 | FAIL | 1269ms | 0% | 1 | ✓ | ✓ | ✓ |
| Q3 | FAIL | 1896ms | 0% | 1 | ✓ | ✓ | ✓ |
| Q4 | FAIL | 1170ms | 0% | 1 | ✓ | ✓ | ✓ |
| Q5 | PASS | 2214ms | 50% | 3 | ✓ | ✓ | ✓ |
| Q6 | PASS | 769ms | 50% | 1 | ✓ | ✓ | ✓ |
| Q7 | PASS | 2243ms | 33% | 1 | ✓ | ✓ | ✓ |
| Q8 | PASS | 2804ms | 100% | 1 | ✓ | ✓ | ✓ |
| Q9 | PASS | 6172ms | 100% | 0 | ✓ | ✓ | ✓ |
| Q10 | FAIL | 3476ms | 75% | 1 | ✗ | ✓ | ✓ |

**Overall: 6/10 passed**

## Test 2 — Retrieval Precision

| ID | Description | Retrieved | Relevant | Precision |
|----|--------------|-----------|----------|-----------|
| P1 | Main entry point query | 1 | 1 | 100% |
| P2 | File I/O query | 1 | 0 | 0% |
| P3 | Error handling query | 1 | 0 | 0% |

**Overall precision: 33% (target: >70%)**

## Test 3 — Latency Regression

| Endpoint | Avg (ms) | Min (ms) | Max (ms) | Target 3000ms |
|----------|----------|----------|----------|---------------|
| GET /health | 2593 | 1488 | 3659 | ✓ PASS |
| GET /stats | 2392 | 2149 | 2851 | ✓ PASS |
| GET /health-dashboard | 2405 | 473 | 4598 | ✓ PASS |
| POST /query | 1636 | 1377 | 1965 | ✓ PASS |
| POST /dependencies | 2496 | 2298 | 2659 | ✓ PASS |
| POST /patterns | 717 | 684 | 763 | ✓ PASS |
| POST /document | 2194 | 1852 | 2403 | ✓ PASS |
| POST /business-logic | 2740 | 2512 | 2868 | ✓ PASS |
| POST /clear-history | 215 | 210 | 225 | ✓ PASS |

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
| 1 | Where is the main entry point of this program? | 1679ms | ✓ |
| 2 | What does that section do in detail? | 1097ms | ✗ |
| 3 | What other paragraphs are near it? | 1422ms | ✗ |
| 4 | What data does it use? | 934ms | ✗ |

**All turns answered: No (1/4)**

## Summary

| Test | Result |
|------|--------|
| Golden Set | 6/10 |
| Retrieval Precision | 33% |
| Latency Regression | Pass |
| Response Shape | Pass |
| Multi-turn | Fail (1/4) |
