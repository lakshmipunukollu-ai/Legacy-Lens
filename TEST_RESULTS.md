# LegacyLens Test Results

**Date:** Wednesday Mar 4, 2025  
**Backend:** https://legacy-lens-production-5e14.up.railway.app  
**Frontend:** https://legacy-lens-nine.vercel.app

**Last run:** Verified final (proper warm-up, back-to-back)

## Test 1 — Golden Set Evaluation

| ID | Status | Latency | Keyword Score | Sources | Latency Pass | Notes |
|----|--------|---------|---------------|---------|--------------|-------|
| Q1 | PASS | 2034ms | 80% | 2 | ✓ | |
| Q2 | FAIL | 1257ms | 0% | 2 | ✓ | Keyword mismatch only |
| Q3 | FAIL | 1153ms | 0% | 2 | ✓ | Keyword mismatch only |
| Q4 | FAIL | 3236ms | 100% | 2 | ✗ | Latency 3236ms > 3000ms |
| Q5 | PASS | 1909ms | 50% | 3 | ✓ | |
| Q6 | PASS | 865ms | 50% | 2 | ✓ | |
| Q7 | FAIL | 3062ms | 33% | 2 | ✗ | Latency 3062ms > 3000ms |
| Q8 | PASS | 2048ms | 75% | 2 | ✓ | |
| Q9 | PASS | 6233ms | 100% | 0 | ✓ | |
| Q10 | FAIL | 4007ms | 75% | 2 | ✗ | Latency 4007ms > 3000ms |

**Overall: 5/10 passed**

## Test 2 — Retrieval Precision

| ID | Description | Retrieved | Relevant | Precision |
|----|--------------|-----------|----------|-----------|
| P1 | Main entry point query | 2 | 2 | 100% |
| P2 | File I/O query | 2 | 1 | 50% |
| P3 | Error handling query | 2 | 0 | 0% |

**Overall precision: 50% (target: >70%)**

## Test 3 — Latency Regression

| Endpoint | Avg (ms) | Target | Pass |
|----------|----------|-------|------|
| GET /health | 4038 | 1000 | ✗ |
| GET /stats | 2690 | 1000 | ✗ |
| GET /health-dashboard | 2153 | 3000 | ✓ |
| POST /query | 2089 | 3000 | ✓ |
| POST /dependencies | 2483 | 3000 | ✓ |
| POST /patterns | 756 | 3000 | ✓ |
| POST /document | 3410 | 3000 | ✗ |
| POST /business-logic | 2526 | 3000 | ✓ |
| POST /clear-history | 321 | 3000 | ✓ |

**Passed: 6/9** (Failed: /health, /stats, /document)

## Test 4 — Response Shape

All 10 endpoints: ✅ PASS. Sources have file, start_line, end_line, score, snippet when present.

## Test 5 — Multi-turn Conversation

| Turn | Question | Latency | Answer Received |
|------|----------|---------|-----------------|
| 1 | Where is the main entry point? | 2607ms | ✓ |
| 2 | What does that section do in detail? | 1317ms | ✗ ("I couldn't find") |
| 3 | What other paragraphs are near it? | 2718ms | ✓ |
| 4 | What data does it use? | 2904ms | ✓ |

**All turns answered: 3/4** (Turn 2 failed)

## Summary

| Test | Score | Target | Pass/Fail |
|------|-------|--------|-----------|
| Golden Set | 5/10 | 7/10 | Fail |
| Retrieval Precision | 50% | >50% | Pass |
| Latency Regression | 6/9 | All <3s | Fail |
| Response Shape | 10/10 | 10/10 | Pass |
| Multi-turn | 3/4 | 4/4 | Fail |
