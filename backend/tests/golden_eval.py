import requests
import json
import time

BASE_URL = "https://legacy-lens-production-5e14.up.railway.app"

GOLDEN_SET = [
    {
        "id": "Q1",
        "endpoint": "/query",
        "input": {"question": "Where is the main entry point of this program?", "session_id": "golden"},
        "expected_keywords": ["main", "entry", "procedure", "division", "program"],
        "expected_has_sources": True,
        "latency_target": 3000
    },
    {
        "id": "Q2",
        "endpoint": "/query",
        "input": {"question": "What functions modify the CUSTOMER-RECORD?", "session_id": "golden"},
        "expected_keywords": ["customer", "record", "move", "modify", "write"],
        "expected_has_sources": True,
        "latency_target": 3000
    },
    {
        "id": "Q3",
        "endpoint": "/query",
        "input": {"question": "Explain what the CALCULATE-INTEREST paragraph does", "session_id": "golden"},
        "expected_keywords": ["interest", "calculate", "paragraph", "compute"],
        "expected_has_sources": True,
        "latency_target": 3000
    },
    {
        "id": "Q4",
        "endpoint": "/query",
        "input": {"question": "Find all file I/O operations", "session_id": "golden"},
        "expected_keywords": ["file", "open", "close", "read", "write", "i/o"],
        "expected_has_sources": True,
        "latency_target": 3000
    },
    {
        "id": "Q5",
        "endpoint": "/dependencies",
        "input": {"question": "What are the dependencies of MODULE-X?"},
        "expected_keywords": ["perform", "call", "depend", "module"],
        "expected_has_sources": True,
        "latency_target": 3000
    },
    {
        "id": "Q6",
        "endpoint": "/patterns",
        "input": {"keyword": "error handling"},
        "expected_keywords": ["error", "handling", "exception", "invalid"],
        "expected_has_sources": True,
        "latency_target": 3000
    },
    {
        "id": "Q7",
        "endpoint": "/document",
        "input": {"paragraph": "main procedure"},
        "expected_keywords": ["procedure", "main", "division"],
        "expected_has_sources": True,
        "latency_target": 3000
    },
    {
        "id": "Q8",
        "endpoint": "/business-logic",
        "input": {"question": "What business rules govern file I/O operations?"},
        "expected_keywords": ["business", "rule", "file", "record"],
        "expected_has_sources": True,
        "latency_target": 3000
    },
    {
        "id": "Q9",
        "endpoint": "/explain-snippet",
        "input": {"code": "PERFORM UNTIL WS-EOF = 'Y'\n  READ INPUT-FILE INTO WS-RECORD\n  AT END MOVE 'Y' TO WS-EOF\n  END-READ\nEND-PERFORM."},
        "expected_keywords": ["loop", "read", "file", "record", "until", "end"],
        "expected_has_sources": False,
        "latency_target": 8000
    },
    {
        "id": "Q10",
        "endpoint": "/query",
        "input": {"question": "Show me error handling patterns in this codebase", "session_id": "golden"},
        "expected_keywords": ["error", "handling", "pattern", "exception"],
        "expected_has_sources": True,
        "latency_target": 3000
    }
]

def get_answer_text(response_json, endpoint):
    if endpoint == "/query":
        return response_json.get("answer", "")
    elif endpoint == "/dependencies":
        return response_json.get("answer", "")
    elif endpoint == "/patterns":
        return str(response_json.get("answer", ""))
    elif endpoint == "/document":
        return response_json.get("documentation", "")
    elif endpoint == "/business-logic":
        return response_json.get("business_logic", "")
    elif endpoint == "/explain-snippet":
        return response_json.get("explanation", "")
    return ""

def run_golden_eval():
    results = []
    passed = 0
    failed = 0

    print("\n" + "="*60)
    print("LEGACYLENS GOLDEN SET EVALUATION")
    print("="*60)

    for test in GOLDEN_SET:
        start = time.time()
        try:
            resp = requests.post(f"{BASE_URL}{test['endpoint']}", json=test["input"], timeout=30)
            latency_ms = round((time.time() - start) * 1000)
            data = resp.json()

            answer_text = get_answer_text(data, test["endpoint"]).lower()
            sources = data.get("sources", [])

            # Check keyword presence
            keywords_found = [k for k in test["expected_keywords"] if k.lower() in answer_text]
            keyword_score = len(keywords_found) / len(test["expected_keywords"])

            # Check sources
            has_sources = len(sources) > 0
            sources_pass = not test["expected_has_sources"] or has_sources

            # Check latency
            latency_pass = latency_ms <= test["latency_target"]

            # Check confidence scores present
            confidence_pass = all("score" in s for s in sources) if sources else True

            # Check file/line references
            file_refs_pass = all("file" in s and "start_line" in s for s in sources) if sources else True

            # Overall pass: keyword score > 0.3, sources present, latency ok
            overall_pass = keyword_score >= 0.3 and sources_pass and latency_pass

            if overall_pass:
                passed += 1
                status = "PASS"
            else:
                failed += 1
                status = "FAIL"

            result = {
                "id": test["id"],
                "status": status,
                "latency_ms": latency_ms,
                "latency_pass": latency_pass,
                "keyword_score": f"{keyword_score:.0%}",
                "keywords_found": keywords_found,
                "keywords_missing": [k for k in test["expected_keywords"] if k.lower() not in answer_text],
                "sources_count": len(sources),
                "confidence_scores_present": confidence_pass,
                "file_line_refs_present": file_refs_pass,
                "answer_preview": answer_text[:100]
            }
            results.append(result)

            print(f"\n[{status}] {test['id']} — {test['endpoint']}")
            print(f"  Latency: {latency_ms}ms (target: {test['latency_target']}ms) {'✓' if latency_pass else '✗'}")
            print(f"  Keywords: {keyword_score:.0%} ({len(keywords_found)}/{len(test['expected_keywords'])}) found: {keywords_found}")
            print(f"  Sources: {len(sources)} {'✓' if sources_pass else '✗'}")
            print(f"  Confidence scores: {'✓' if confidence_pass else '✗'}")
            print(f"  File/line refs: {'✓' if file_refs_pass else '✗'}")

        except Exception as e:
            failed += 1
            results.append({"id": test["id"], "status": "ERROR", "error": str(e)})
            print(f"\n[ERROR] {test['id']}: {e}")

    print("\n" + "="*60)
    print(f"GOLDEN SET RESULTS: {passed}/{len(GOLDEN_SET)} passed ({passed/len(GOLDEN_SET):.0%})")
    print("="*60)
    return results, passed, failed

if __name__ == "__main__":
    # Warm up with a real query to initialize Pinecone + OpenAI connections
    print("Warming up backend...")
    try:
        requests.post(f"{BASE_URL}/query",
            json={"question": "Where is the main entry point?", "session_id": "warmup"},
            timeout=30)
        print("Backend warm.")
    except Exception:
        pass
    time.sleep(2)

    results, passed, failed = run_golden_eval()
    with open("golden_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to golden_results.json")
