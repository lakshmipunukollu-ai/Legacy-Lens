# LegacyLens Test Results

**Date:** Wednesday Mar 4, 2025  
**Backend:** https://legacy-lens-production-5e14.up.railway.app  
**Frontend:** https://legacy-lens-nine.vercel.app

**Last run:** Final test suite (warm-up + back-to-back)

## Test 1 — Golden Set Evaluation

| ID | Status | Latency | Keyword Score | Sources | Latency Pass | Confidence | File/Line Refs |
|----|--------|---------|---------------|---------|--------------|------------|----------------|
| Q1 | FAIL | 4830ms | 80% | 2 | ✗ | ✓ | ✓ |
| Q2 | FAIL | 1741ms | 0% | 2 | ✓ | ✓ | ✓ |
| Q3 | FAIL | 1671ms | 0% | 2 | ✓ | ✓ | ✓ |
| Q4 | FAIL | 3847ms | 100% | 2 | ✗ | ✓ | ✓ |
| Q5 | PASS | 2777ms | 50% | 3 | ✓ | ✓ | ✓ |
| Q6 | PASS | 1024ms | 50% | 2 | ✓ | ✓ | ✓ |
| Q7 | FAIL | 3376ms | 33% | 2 | ✗ | ✓ | ✓ |
| Q8 | FAIL | 4087ms | 75% | 2 | ✗ | ✓ | ✓ |
| Q9 | PASS | 6024ms | 100% | 0 | ✓ | ✓ | ✓ |
| Q10 | FAIL | 4243ms | 75% | 2 | ✗ | ✓ | ✓ |

**Overall: 3/10 passed**

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
| GET /health | 4824 | 1963 | 6607 | ✗ FAIL |
| GET /stats | 4282 | 2883 | 5947 | ✗ FAIL |
| GET /health-dashboard | 2464 | 462 | 4746 | ✓ PASS |
| POST /query | 1993 | 1939 | 2092 | ✓ PASS |
| POST /dependencies | 2699 | 2615 | 2865 | ✓ PASS |
| POST /patterns | 1032 | 762 | 1545 | ✓ PASS |
| POST /document | 2671 | 2513 | 2826 | ✓ PASS |
| POST /business-logic | 2432 | 2359 | 2495 | ✓ PASS |
| POST /clear-history | 212 | 168 | 239 | ✓ PASS |

**All endpoints under 3,000ms: No** (GET /health, GET /stats exceeded — Railway cold start)

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
| 1 | Where is the main entry point of this program? | 2545ms | ✓ |
| 2 | What does that section do in detail? | 2414ms | ✓ |
| 3 | What other paragraphs are near it? | 3109ms | ✓ |
| 4 | What data does it use? | 4330ms | ✓ |

**All turns answered: 4/4**

## Summary

| Test | Result |
|------|--------|
| Golden Set | 3/10 |
| Retrieval Precision | 50% |
| Latency Regression | Fail |
| Response Shape | Pass |
| Multi-turn | Pass (4/4) |
