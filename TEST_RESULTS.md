# LegacyLens Test Results

**Date:** Wednesday Mar 4, 2025  
**Backend:** https://legacy-lens-production-5e14.up.railway.app  
**Frontend:** https://legacy-lens-nine.vercel.app

**Last run:** Post-fix (client-side history, TOP_K=2, error handling patterns trigger)

## Test 1 — Golden Set Evaluation

| ID | Status | Latency | Keyword Score | Sources | Latency Pass | Confidence | File/Line Refs |
|----|--------|---------|---------------|---------|--------------|------------|----------------|
| Q1 | FAIL | 3569ms | 80% | 2 | ✗ | ✓ | ✓ |
| Q2 | FAIL | 1390ms | 0% | 2 | ✓ | ✓ | ✓ |
| Q3 | FAIL | 1358ms | 0% | 2 | ✓ | ✓ | ✓ |
| Q4 | FAIL | 3640ms | 100% | 2 | ✗ | ✓ | ✓ |
| Q5 | PASS | 2095ms | 50% | 3 | ✓ | ✓ | ✓ |
| Q6 | PASS | 819ms | 50% | 2 | ✓ | ✓ | ✓ |
| Q7 | FAIL | 3053ms | 33% | 2 | ✗ | ✓ | ✓ |
| Q8 | PASS | 2702ms | 100% | 2 | ✓ | ✓ | ✓ |
| Q9 | PASS | 7250ms | 100% | 0 | ✓ | ✓ | ✓ |
| Q10 | FAIL | 4401ms | 75% | 2 | ✗ | ✓ | ✓ |

**Overall: 4/10 passed**

*Note: Q4 improved from 0% to 100% keywords with TOP_K=2. Some queries exceed 3000ms latency target due to retrieving 2 chunks.*

## Test 2 — Retrieval Precision

| ID | Description | Retrieved | Relevant | Precision |
|----|--------------|-----------|----------|-----------|
| P1 | Main entry point query | 2 | 2 | 100% |
| P2 | File I/O query | 2 | 1 | 50% |
| P3 | Error handling query | 2 | 0 | 0% |

**Overall precision: 50% (target: >70%)**

*Note: Improved from 33% with TOP_K=2. P2 improved from 0% to 50% relevant chunks.*

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
| 1 | Where is the main entry point of this program? | 3379ms | ✓ |
| 2 | What does that section do in detail? | 1882ms | ✓ |
| 3 | What other paragraphs are near it? | 2408ms | ✓ |
| 4 | What data does it use? | 3058ms | ✓ |

**All turns answered: Yes (4/4)**

*Note: Client-side history fix — conversation context now persists across turns. Railway restarts no longer break multi-turn.*

## Summary

| Test | Result |
|------|--------|
| Golden Set | 4/10 |
| Retrieval Precision | 50% |
| Latency Regression | Pass |
| Response Shape | Pass |
| Multi-turn | Pass (4/4) |
