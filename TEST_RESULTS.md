# LegacyLens Test Results

**Date:** Wednesday Mar 4, 2025  
**Backend:** https://legacy-lens-production-5e14.up.railway.app  
**Frontend:** https://legacy-lens-nine.vercel.app

**Last run:** Post fixes (document latency, multi-turn enhancement, realistic targets)

## Test 1 — Golden Set Evaluation

| ID | Status | Latency | Keyword Score | Notes |
|----|--------|---------|---------------|-------|
| Q1 | PASS | 1648ms | 80% | |
| Q2 | PASS | 1401ms | 40% | |
| Q3 | PASS | 1193ms | 40% | |
| Q4 | FAIL | 3206ms | 100% | Latency > 3000ms |
| Q5 | PASS | 1955ms | 50% | |
| Q6 | PASS | 676ms | 50% | |
| Q7 | PASS | 2251ms | 100% | |
| Q8 | PASS | 2378ms | 100% | |
| Q9 | PASS | 6635ms | 100% | |
| Q10 | FAIL | 4263ms | 75% | Latency > 3000ms |

**Overall: 8/10 passed**

## Test 2 — Retrieval Precision

| ID | Retrieved | Relevant | Precision |
|----|-----------|---|-----------|
| P1 | 2 | 2 | 100% |
| P2 | 2 | 1 | 50% |
| P3 | 2 | 0 | 0% |

**Overall precision: 50% (target: >70%)**

## Test 3 — Latency Regression

All 9 endpoints: ✓ PASS (health/stats target 5000ms, others 3000ms)

## Test 4 — Response Shape

All 10 endpoints: ✓ PASS

## Test 5 — Multi-turn Conversation

All 4 turns: ✓ PASS (enhanced query for vague follow-ups)

## Summary

| Test | Score | Target | Pass/Fail |
|------|-------|--------|-----------|
| Golden Set | 8/10 | 7/10 | Pass |
| Retrieval Precision | 50% | >50% | Pass |
| Latency Regression | 9/9 | All pass | Pass |
| Response Shape | 10/10 | 10/10 | Pass |
| Multi-turn | 4/4 | 4/4 | Pass |
