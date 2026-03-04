# LegacyLens Test Results

**Date:** Wednesday Mar 4, 2025  
**Backend:** https://legacy-lens-production-5e14.up.railway.app  
**Frontend:** https://legacy-lens-nine.vercel.app

**Last run:** Final (proper /query warm-up, realistic latency targets)

## Test 1 — Golden Set Evaluation

| ID | Status | Latency | Keyword Score | Sources | Latency Pass | Confidence | File/Line Refs |
|----|--------|---------|---------------|---------|--------------|------------|----------------|
| Q1 | PASS | 2819ms | 80% | 2 | ✓ | ✓ | ✓ |
| Q2 | FAIL | 1120ms | 0% | 2 | ✓ | ✓ | ✓ |
| Q3 | FAIL | 1107ms | 0% | 2 | ✓ | ✓ | ✓ |
| Q4 | PASS | 2761ms | 100% | 2 | ✓ | ✓ | ✓ |
| Q5 | PASS | 2083ms | 50% | 3 | ✓ | ✓ | ✓ |
| Q6 | PASS | 918ms | 50% | 2 | ✓ | ✓ | ✓ |
| Q7 | PASS | 2840ms | 33% | 2 | ✓ | ✓ | ✓ |
| Q8 | PASS | 2562ms | 75% | 2 | ✓ | ✓ | ✓ |
| Q9 | PASS | 5412ms | 100% | 0 | ✓ | ✓ | ✓ |
| Q10 | FAIL | 4123ms | 75% | 2 | ✗ | ✓ | ✓ |

**Overall: 7/10 passed**

*Warm-up: /query before tests to initialize Pinecone + OpenAI.*

## Test 2 — Retrieval Precision

| ID | Description | Retrieved | Relevant | Precision |
|----|--------------|-----------|----------|-----------|
| P1 | Main entry point query | 2 | 2 | 100% |
| P2 | File I/O query | 2 | 1 | 50% |
| P3 | Error handling query | 2 | 0 | 0% |

**Overall precision: 50% (target: >70%)**

## Test 3 — Latency Regression

| Endpoint | Avg (ms) | Min (ms) | Max (ms) | Target | Pass |
|----------|----------|----------|----------|--------|------|
| GET /health | 5362* | 4549 | 6174 | 1000 | ✗ |
| GET /stats | 2452* | 2121 | 2783 | 1000 | ✗ |
| GET /health-dashboard | 2446 | 509 | 4254 | 3000 | ✓ |
| POST /query | 2022 | 1901 | 2109 | 3000 | ✓ |
| POST /dependencies | 2637 | 2355 | 3129 | 3000 | ✓ |
| POST /patterns | 736 | 668 | 790 | 3000 | ✓ |
| POST /document | 2618 | 2327 | 2900 | 3000 | ✓ |
| POST /business-logic | 2613 | 2185 | 2991 | 3000 | ✓ |
| POST /clear-history | 236 | 227 | 246 | 3000 | ✓ |

*Health/stats: avg of runs 2–3 (skip cold start). Target 1000ms.*

**All endpoints pass: No** (health, stats exceed 1000ms — Railway network latency)

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
| 1 | Where is the main entry point of this program? | 1893ms | ✓ |
| 2 | What does that section do in detail? | 2813ms | ✓ |
| 3 | What other paragraphs are near it? | 3630ms | ✓ |
| 4 | What data does it use? | 2395ms | ✓ |

**All turns answered: 4/4**

## Summary

| Test | Result |
|------|--------|
| Golden Set | 7/10 |
| Retrieval Precision | 50% |
| Latency Regression | Fail |
| Response Shape | Pass |
| Multi-turn | Pass (4/4) |
